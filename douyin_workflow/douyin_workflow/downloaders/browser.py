"""Anonymous Chromium backend for current Douyin web signatures.

The browser context is always ephemeral: no persistent profile and no user
login state are read. It captures the official aweme detail response, then
closes Chromium before streaming the source video.
"""

from __future__ import annotations

from pathlib import Path

import requests

from .base import DownloadError, UnsupportedContent, VideoInfo, stream_to_file
from .iesdouyin import item_to_info, play_urls


class BrowserBackend:
    name = "browser"

    def __init__(self, executable_path: str | None = None, timeout: float = 20):
        self.executable_path = executable_path
        self.timeout = timeout

    def fetch_item(self, aweme_id: str) -> tuple[dict, list[dict], str]:
        browser_path: Path | None = None
        if self.executable_path:
            browser_path = Path(self.executable_path).expanduser()
            if not browser_path.is_file():
                raise DownloadError("配置的 Chromium 可执行文件不存在")
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise DownloadError("未安装 Playwright（pip install -e '.[browser]'）") from exc

        launch_options: dict = {"headless": True, "args": ["--disable-dev-shm-usage"]}
        if browser_path:
            launch_options["executable_path"] = str(browser_path)

        timeout_ms = max(1, int(self.timeout * 1000))
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(**launch_options)
                try:
                    context = browser.new_context(locale="zh-CN")
                    page = context.new_page()
                    with page.expect_response(
                        lambda response: "/aweme/v1/web/aweme/detail/" in response.url
                        and response.status == 200,
                        timeout=timeout_ms,
                    ) as response_info:
                        page.goto(
                            f"https://www.douyin.com/video/{aweme_id}",
                            wait_until="domcontentloaded",
                            timeout=timeout_ms,
                        )
                    payload = response_info.value.json()
                    item = payload.get("aweme_detail") if isinstance(payload, dict) else None
                    cookies = context.cookies()
                    user_agent = page.evaluate("navigator.userAgent")
                finally:
                    browser.close()
        except DownloadError:
            raise
        except Exception as exc:
            # Playwright errors may contain signed URLs; keep them out of logs.
            raise DownloadError(f"匿名浏览器取详情失败：{type(exc).__name__}") from exc

        if not isinstance(item, dict):
            raise DownloadError("抖音详情接口没有返回作品数据，匿名会话可能被风控")
        return item, cookies, str(user_agent)

    def download(self, url: str, aweme_id: str, out_dir: Path) -> VideoInfo:
        item, cookies, user_agent = self.fetch_item(aweme_id)
        if item.get("images") and not (item.get("video") or {}).get("play_addr", {}).get("url_list"):
            raise UnsupportedContent("这是图文作品，没有视频可转写")
        urls = play_urls(item)
        if not urls:
            raise DownloadError("作品详情里没有播放地址")

        session = requests.Session()
        for cookie in cookies:
            name, value = str(cookie.get("name") or ""), str(cookie.get("value") or "")
            if not name:
                continue
            session.cookies.set(
                name,
                value,
                domain=str(cookie.get("domain") or "www.douyin.com"),
                path=str(cookie.get("path") or "/"),
            )

        info = item_to_info(item, aweme_id)
        dest = out_dir / "video.mp4"
        info.source_url = stream_to_file(
            urls,
            dest,
            session,
            self.timeout,
            referer=f"https://www.douyin.com/video/{aweme_id}",
            user_agent=user_agent,
        )
        info.video_path = dest
        info.backend = self.name
        return info
