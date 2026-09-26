"""命令行入口。

    python -m douyin_workflow run "<分享口令>"      # 下载 + 转写，打印逐字稿
    python -m douyin_workflow list                   # 本地素材库
    python -m douyin_workflow healthcheck            # 逐个后端测固定链接，失败推送告警

healthcheck 退出码：0 全部正常；1 有后端坏了但还能降级；2 全部失败。
告警：设置 DOUYIN_ALERT_WEBHOOK 为一个接收 JSON {"title","body"} 的地址（例如 Bark
的 https://api.day.app/<key>），有后端失败时 POST 过去。
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import requests

from .config import get_settings
from .downloaders import AllBackendsFailed, DownloadChain, UnsupportedContent, build_backends
from .share import ShareParseError, resolve
from .transcribe import TranscribeError

def cmd_run(args) -> int:
    from .pipeline import douyin_to_text

    res = douyin_to_text(args.share_text, force=args.force)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"# {res.get('title')}\n作者：{res.get('author')}  时长：{res.get('duration_s')}s  "
              f"后端：{res.get('backend')}{'（缓存）' if res.get('cached') else ''}\n")
        print(res["transcript"])
    return 0


def cmd_list(args) -> int:
    from .pipeline import list_local

    for m in list_local(args.limit):
        print(f"{m['created_at']}  {m['aweme_id']}  {m['duration_s']}s  {m['author']}  {m['title'][:40]}")
    return 0


def healthcheck(urls: list[str]) -> dict[str, dict]:
    """每个后端单独跑一遍，只测下载，不转写。"""
    settings = get_settings()
    report: dict[str, dict] = {}
    for name in settings.backends:
        backend = build_backends(replace(settings, backends=[name]))[0]
        ok, errors = 0, []
        for u in urls:
            try:
                url, aweme_id = resolve(u, timeout=settings.timeout)
                with tempfile.TemporaryDirectory() as d:
                    DownloadChain([backend]).download(url, aweme_id, Path(d))
                ok += 1
            except UnsupportedContent as e:
                errors.append(f"测试链接不可用，请换一个：{e}")
            except Exception as e:
                errors.append(str(e))
        report[name] = {"ok": ok, "total": len(urls), "errors": errors}
    return report


def notify(title: str, body: str) -> None:
    hook = os.getenv("DOUYIN_ALERT_WEBHOOK")
    if not hook:
        return
    try:
        requests.post(hook, json={"title": title, "body": body}, timeout=10)
    except requests.RequestException as e:
        print(f"告警推送失败：{e}", file=sys.stderr)


def cmd_healthcheck(args) -> int:
    # 挑 1~3 条自己确认过、长期不会删的公开作品链接，逗号分隔
    urls = [u.strip() for u in os.getenv("DOUYIN_HEALTH_URLS", "").split(",") if u.strip()]
    if not urls:
        print("请先设置 DOUYIN_HEALTH_URLS（逗号分隔的固定作品链接）", file=sys.stderr)
        return 2
    report = healthcheck(urls)
    broken = [n for n, r in report.items() if r["ok"] < r["total"]]
    alive = [n for n, r in report.items() if r["ok"] > 0]
    for n, r in report.items():
        status = "OK " if n not in broken else "BAD"
        print(f"[{status}] {n}: {r['ok']}/{r['total']}")
        for e in r["errors"]:
            print(f"      {e[:200]}")
    if not broken:
        return 0
    level = 2 if not alive else 1
    title = "抖音下载：全部后端失败" if level == 2 else f"抖音下载：{','.join(broken)} 异常"
    body = "\n".join(f"{n}: {'; '.join(report[n]['errors'])[:300]}" for n in broken)
    notify(title, body)
    return level


def cmd_serve(args) -> int:
    from .server import App, make_server

    token = os.getenv("DOUYIN_SERVER_TOKEN")
    if not token:
        import secrets

        print("请先设置 DOUYIN_SERVER_TOKEN，例如：", file=sys.stderr)
        print(f"  export DOUYIN_SERVER_TOKEN={secrets.token_hex(16)}", file=sys.stderr)
        return 2
    srv = make_server(App(token, wait_s=args.wait), args.host, args.port)
    print(f"已启动：http://{args.host}:{args.port}/transcribe", file=sys.stderr)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser(prog="douyin_workflow")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="下载并转写一条分享口令")
    r.add_argument("share_text")
    r.add_argument("--force", action="store_true", help="忽略缓存重新处理")
    r.add_argument("--json", action="store_true", help="输出完整 JSON")
    r.set_defaults(func=cmd_run)

    ls = sub.add_parser("list", help="列出本地素材库")
    ls.add_argument("--limit", type=int, default=20)
    ls.set_defaults(func=cmd_list)

    h = sub.add_parser("healthcheck", help="逐个后端测试固定链接")
    h.set_defaults(func=cmd_healthcheck)

    sv = sub.add_parser("serve", help="启动给 iPhone 快捷指令用的 HTTP 服务")
    sv.add_argument("--host", default=os.getenv("DOUYIN_SERVER_HOST", "0.0.0.0"))
    sv.add_argument("--port", type=int, default=int(os.getenv("DOUYIN_SERVER_PORT", "8765")))
    sv.add_argument("--wait", type=float, default=25, help="单次请求最多等几秒")
    sv.set_defaults(func=cmd_serve)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except AllBackendsFailed as e:
        print("所有下载后端都失败了（cookie 过期 / 被风控 / 页面改版），各后端原因：", file=sys.stderr)
        for name, err in e.errors.items():
            print(f"  [{name}] {err[:300]}", file=sys.stderr)
        return 3
    except (ShareParseError, UnsupportedContent, TranscribeError, requests.RequestException) as e:
        print(f"失败：{e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
