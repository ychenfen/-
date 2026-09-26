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
import re
import secrets
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout  # 3.10 里它和内置 TimeoutError 不是同一个类
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

import requests

from . import pipeline
from .config import Settings, get_settings
from .media import cleanup_retained_videos, create_workbench_bundle, retained_video
from .share import ShareParseError, resolve
from .web_page import INDEX_HTML

log = logging.getLogger(__name__)

MAX_BODY = 64 * 1024


def format_done(res: dict) -> str:
    head = res.get("title") or "（无标题）"
    meta = " · ".join(x for x in [res.get("author"), f"{res['duration_s']}秒" if res.get("duration_s") else ""] if x)
    return f"{head}\n{meta}\n\n{res.get('transcript', '')}".strip()


def done_payload(res: dict, aweme_id: str, cached: bool, video_available: bool = False) -> dict:
    """保留旧客户端需要的 text，同时给网页提供可编辑的结构化结果。"""
    return {
        "status": "done",
        "text": format_done(res),
        "aweme_id": aweme_id,
        "cached": cached,
        "title": res.get("title") or "",
        "author": res.get("author") or "",
        "duration_s": res.get("duration_s"),
        "transcript": res.get("transcript") or "",
        "backend": res.get("backend") or "",
        "timing_s": res.get("timing_s") or {},
        "video_available": video_available,
    }


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
        cleanup_retained_videos(self.settings)
        try:
            url, aweme_id = self.resolver(share_text)
        except ShareParseError as e:
            return {"status": "error", "text": f"没认出抖音链接：{e}"}
        except requests.RequestException as e:
            return {"status": "error", "text": f"解析短链时网络出错：{e}"}

        cached = pipeline.load_cached(self.settings.data_dir / aweme_id)
        if cached:
            return done_payload(cached, aweme_id, True, retained_video(self.settings, aweme_id) is not None)

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
        return done_payload(res, aweme_id, False, retained_video(self.settings, aweme_id) is not None)


def _handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def _html_headers(self) -> bytes:
            nonce = secrets.token_urlsafe(18)
            data = INDEX_HTML.replace("__CSP_NONCE__", nonce).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Permissions-Policy",
                "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
            )
            self.send_header(
                "Content-Security-Policy",
                "; ".join(
                    (
                        "default-src 'none'",
                        "base-uri 'none'",
                        "connect-src 'self'",
                        "img-src data:",
                        f"style-src 'nonce-{nonce}'",
                        f"script-src 'nonce-{nonce}'",
                        "object-src 'none'",
                        "frame-ancestors 'none'",
                        "form-action 'none'",
                    )
                ),
            )
            self.end_headers()
            return data

        def _send(self, code: int, body: dict) -> None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_file(self, path, content_type: str, filename: str, remove_after: bool = False) -> None:
            try:
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(path.stat().st_size))
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Cache-Control", "private, no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                log.info("客户端下载中断 %s", filename)
            finally:
                if remove_after:
                    path.unlink(missing_ok=True)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/health":
                return self._send(200, {"ok": True})
            if path in ("/", "/index.html"):
                self.wfile.write(self._html_headers())
                return
            media_match = re.fullmatch(r"/media/([0-9]{10,25})/video", path)
            if media_match:
                if not app.authorized(self.headers.get("Authorization")):
                    return self._send(401, {"status": "error", "text": "访问密码不对"})
                cleanup_retained_videos(app.settings)
                video = retained_video(app.settings, media_match.group(1))
                if video is None:
                    return self._send(404, {"status": "error", "text": "原视频未保留或已经过期"})
                return self._send_file(video, "video/mp4", f"douyin-{media_match.group(1)}{video.suffix.lower()}")
            self._send(404, {"status": "error", "text": "not found"})

        def do_HEAD(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                self._html_headers()
                return
            if path == "/health":
                data = json.dumps({"ok": True}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                return
            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            if self.path not in ("/transcribe", "/bundle"):
                return self._send(404, {"status": "error", "text": "not found"})
            if not app.authorized(self.headers.get("Authorization")):
                return self._send(401, {"status": "error", "text": "口令（token）不对，检查快捷指令里的 Authorization"})
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._send(413, {"status": "error", "text": "内容太长"})
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            try:
                body = json.loads(raw)
            except (json.JSONDecodeError, AttributeError):
                body = None
            if self.path == "/bundle":
                if not isinstance(body, dict):
                    return self._send(400, {"status": "error", "text": "请求格式不对"})
                aweme_id = str(body.get("aweme_id") or "")
                transcript = str(body.get("transcript") or "")
                try:
                    bundle = create_workbench_bundle(app.settings, aweme_id, transcript)
                except (FileNotFoundError, ValueError) as error:
                    return self._send(404, {"status": "error", "text": str(error)})
                return self._send_file(bundle, "application/zip", f"douyin-{aweme_id}-workbench.zip", True)
            text = body.get("text", "") if isinstance(body, dict) else raw
            self._send(200, app.transcribe(str(text)))

        def log_message(self, fmt, *args):
            log.info("%s %s", self.address_string(), fmt % args)

    return Handler


def make_server(app: App, host: str = "0.0.0.0", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _handler(app))
