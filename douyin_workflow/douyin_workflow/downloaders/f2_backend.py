"""后端 2：f2（pip install f2），走 douyin.com 的签名接口（a_bogus），需要网页版 cookie。

只借用 f2 的签名和接口请求拿元数据，视频文件仍由我们自己流式下载，方便统一校验。
f2 的内部 API 会随版本变化，这里全部防御式取值；f2 导入时就会联网生成 msToken，
导入或请求失败都当作这个后端不可用，交给下一个后端。
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from .base import DownloadError, UnsupportedContent, VideoInfo, stream_to_file

DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


class F2Backend:
    name = "f2"

    def __init__(self, cookie: str | None, timeout: float = 20, session: requests.Session | None = None):
        self.cookie = cookie
        self.timeout = timeout
        self.session = session or requests.Session()

    async def _fetch(self, aweme_id: str):
        from f2.apps.douyin.handler import DouyinHandler

        kwargs = {
            "headers": {"User-Agent": DESKTOP_UA, "Referer": "https://www.douyin.com/"},
            "cookie": self.cookie,
            "proxies": {"http://": None, "https://": None},
            "timeout": int(self.timeout),
        }
        return await DouyinHandler(kwargs).fetch_one_video(aweme_id)

    def download(self, url: str, aweme_id: str, out_dir: Path) -> VideoInfo:
        if not self.cookie:
            raise DownloadError("未配置 DOUYIN_COOKIE，跳过 f2")
        try:
            import f2  # noqa: F401
        except ImportError as e:
            raise DownloadError("未安装 f2（pip install f2）") from e

        try:
            # 单独开线程跑事件循环：调用方（如 mcp 1.x）自己可能就在事件循环里
            with ThreadPoolExecutor(max_workers=1) as ex:
                video = ex.submit(asyncio.run, self._fetch(aweme_id)).result()
        except Exception as e:  # f2 抛的异常类型不稳定，统一转成 DownloadError
            raise DownloadError(f"f2 获取作品失败：{type(e).__name__}: {e}") from e

        urls = getattr(video, "video_play_addr", None) or []
        if isinstance(urls, str):
            urls = [urls]
        if not urls:
            if getattr(video, "images", None):
                raise UnsupportedContent("这是图文作品，没有视频可转写")
            raise DownloadError("f2 返回里没有播放地址")

        duration_ms = getattr(video, "duration", None)
        info = VideoInfo(
            aweme_id=str(getattr(video, "aweme_id", None) or aweme_id),
            title=(getattr(video, "desc_raw", None) or getattr(video, "desc", None) or "").strip(),
            author=(getattr(video, "nickname_raw", None) or getattr(video, "nickname", None) or "").strip(),
            duration_s=round(duration_ms / 1000, 1) if isinstance(duration_ms, (int, float)) else None,
        )
        dest = out_dir / "video.mp4"
        info.source_url = stream_to_file(list(urls), dest, self.session, self.timeout)
        info.video_path = dest
        info.backend = self.name
        return info
