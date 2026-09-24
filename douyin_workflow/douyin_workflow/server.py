"""给 iPhone 快捷指令用的 HTTP 服务。

    DOUYIN_SERVER_TOKEN=<随机串> python -m douyin_workflow serve

快捷指令把分享口令 POST 到 /transcribe（带 Authorization: Bearer <token>）。
下载 + 转写可能要一两分钟，而手机端单次请求不宜挂太久，所以：
- 每次请求最多等 wait_s 秒；做完了返回 status=done，没做完返回 status=running；
- 快捷指令循环重发同一条口令即可。服务端按作品 ID 去重，重发不会重复下载，
  已经做完的作品直接读缓存秒回。

响应永远是 200 + JSON（鉴权失败除外），手机端只要看 status 和 text 两个字段：
    {"status": "done" | "running" | "error", "text": "给人看的一段文字", ...}
"""

from __future__ import annotations

import hmac
import json
import logging
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout  # 3.10 里它和内置 TimeoutError 不是同一个类
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

import requests

from . import pipeline
from .config import Settings, get_settings
from .share import ShareParseError, resolve
from .web_page import INDEX_HTML

log = logging.getLogger(__name__)

MAX_BODY = 64 * 1024


def format_done(res: dict) -> str:
    head = res.get("title") or "（无标题）"
    meta = " · ".join(x for x in [res.get("author"), f"{res['duration_s']}秒" if res.get("duration_s") else ""] if x)
    return f"{head}\n{meta}\n\n{res.get('transcript', '')}".strip()


class Jobs:
    """按作品 ID 去重的后台任务。转写本身是串行的，所以只开一个工作线程。"""

    def __init__(self, runner: Callable[[str], dict]):
        self.runner = runner
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="douyin-job")
        self.jobs: dict[str, tuple[Future, float]] = {}
        self.lock = threading.Lock()

    def get_or_start(self, aweme_id: str, url: str) -> tuple[Future, float]:
        with self.lock:
            if aweme_id not in self.jobs:
                self.jobs[aweme_id] = (self.pool.submit(self.runner, url), time.monotonic())
            return self.jobs[aweme_id]

    def finish(self, aweme_id: str) -> None:
        with self.lock:
            self.jobs.pop(aweme_id, None)


class App:
    def __init__(
        self,
        token: str,
        settings: Settings | None = None,
        runner: Callable[[str], dict] | None = None,
        resolver: Callable[[str], tuple[str, str]] | None = None,
        wait_s: float = 25,
    ):
        self.token = token
        self.settings = settings or get_settings()
        self.resolver = resolver or (lambda t: resolve(t, timeout=self.settings.timeout))
        self.jobs = Jobs(runner or (lambda url: pipeline.run_safe(url, settings=self.settings)))
        self.wait_s = wait_s

    def authorized(self, header: str | None) -> bool:
        expected = f"Bearer {self.token}"
        return bool(header) and hmac.compare_digest(header.encode(), expected.encode())

    def transcribe(self, share_text: str) -> dict:
        try:
            url, aweme_id = self.resolver(share_text)
        except ShareParseError as e:
            return {"status": "error", "text": f"没认出抖音链接：{e}"}
        except requests.RequestException as e:
            return {"status": "error", "text": f"解析短链时网络出错：{e}"}

        cached = pipeline.load_cached(self.settings.data_dir / aweme_id)
        if cached:
            return {"status": "done", "text": format_done(cached), "aweme_id": aweme_id, "cached": True}

        future, started = self.jobs.get_or_start(aweme_id, url)
        try:
            res = future.result(timeout=self.wait_s)
        except FutureTimeout:
            waited = int(time.monotonic() - started)
            return {"status": "running", "text": f"正在下载和转写，已处理 {waited} 秒…", "aweme_id": aweme_id}
        except Exception as e:  # runner 里的意外异常
            self.jobs.finish(aweme_id)
            log.exception("任务异常 %s", aweme_id)
            return {"status": "error", "text": f"处理失败：{type(e).__name__}: {e}", "aweme_id": aweme_id}

        # 结果已经取走（成功的已落盘缓存；失败的清掉，下次重发会重新尝试）
        self.jobs.finish(aweme_id)
        if "error" in res:
            return {"status": "error", "text": f"处理失败：{res['message']}", "aweme_id": aweme_id, **res}
        return {"status": "done", "text": format_done(res), "aweme_id": aweme_id, "cached": False}


def _handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: dict) -> None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/health":
                return self._send(200, {"ok": True})
            if path in ("/", "/index.html"):
                data = INDEX_HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(data)
                return
            self._send(404, {"status": "error", "text": "not found"})

        def do_POST(self):
            if self.path != "/transcribe":
                return self._send(404, {"status": "error", "text": "not found"})
            if not app.authorized(self.headers.get("Authorization")):
                return self._send(401, {"status": "error", "text": "口令（token）不对，检查快捷指令里的 Authorization"})
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._send(413, {"status": "error", "text": "内容太长"})
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            try:
                text = json.loads(raw).get("text", "")
            except (json.JSONDecodeError, AttributeError):
                text = raw  # 也接受纯文本 body
            self._send(200, app.transcribe(str(text)))

        def log_message(self, fmt, *args):
            log.info("%s %s", self.address_string(), fmt % args)

    return Handler


def make_server(app: App, host: str = "0.0.0.0", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _handler(app))
