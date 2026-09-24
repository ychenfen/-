"""后端 1：直接解析 iesdouyin.com 分享页里的 window._ROUTER_DATA。

最轻、不需要 cookie；抖音改页面结构时最先坏，坏了由后面的后端兜底。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import requests

from ..share import MOBILE_UA
from .base import DownloadError, UnsupportedContent, VideoInfo, stream_to_file

_ROUTER_RE = re.compile(r"window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*</script>", re.S)


def parse_share_page(html: str) -> dict:
    """从分享页 HTML 里取出作品 item（dict）。"""
    m = _ROUTER_RE.search(html)
    if not m:
        raise DownloadError("分享页里没找到 _ROUTER_DATA，页面结构可能变了")
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        raise DownloadError(f"_ROUTER_DATA 不是合法 JSON：{e}") from e

    for page in (data.get("loaderData") or {}).values():
        if not isinstance(page, dict) or "videoInfoRes" not in page:
            continue
        res = page["videoInfoRes"] or {}
        items = res.get("item_list") or []
        if items:
            return items[0]
        filtered = res.get("filter_list") or []
        if filtered:
            reason = filtered[0].get("filter_reason") or filtered[0].get("detail_msg") or "unknown"
            raise UnsupportedContent(f"作品不可用（已删除/私密/审核中）：{reason}")
    raise DownloadError("_ROUTER_DATA 里没有 videoInfoRes，页面结构可能变了")


def play_urls(item: dict) -> list[str]:
    """无水印播放地址候选：playwm → play，再加上按 uri 拼的备用地址。"""
    video = item.get("video") or {}
    play = video.get("play_addr") or {}
    urls = [u.replace("playwm", "play") for u in play.get("url_list") or []]
    uri = play.get("uri")
    if uri and not uri.startswith("http"):
        urls.append(f"https://aweme.snssdk.com/aweme/v1/play/?video_id={uri}&ratio=1080p&line=0")
    # 去重但保留顺序
    return list(dict.fromkeys(urls))


def item_to_info(item: dict, aweme_id: str) -> VideoInfo:
    video = item.get("video") or {}
    duration_ms = video.get("duration") or item.get("duration")
    return VideoInfo(
        aweme_id=str(item.get("aweme_id") or aweme_id),
        title=(item.get("desc") or "").strip(),
        author=((item.get("author") or {}).get("nickname") or "").strip(),
        duration_s=round(duration_ms / 1000, 1) if duration_ms else None,
        extra={
            "create_time": item.get("create_time"),
            "statistics": item.get("statistics") or {},
        },
    )


class IesDouyinBackend:
    name = "iesdouyin"

    def __init__(self, timeout: float = 20, session: requests.Session | None = None):
        self.timeout = timeout
        self.session = session or requests.Session()

    def fetch_item(self, aweme_id: str) -> dict:
        page = f"https://www.iesdouyin.com/share/video/{aweme_id}/"
        try:
            r = self.session.get(page, headers={"User-Agent": MOBILE_UA}, timeout=self.timeout)
            r.raise_for_status()
        except requests.RequestException as e:
            raise DownloadError(f"分享页请求失败：{e}") from e
        return parse_share_page(r.text)

    def download(self, url: str, aweme_id: str, out_dir: Path) -> VideoInfo:
        item = self.fetch_item(aweme_id)
        if item.get("images") and not (item.get("video") or {}).get("play_addr", {}).get("url_list"):
            raise UnsupportedContent("这是图文作品，没有视频可转写")
        urls = play_urls(item)
        if not urls:
            raise DownloadError("item 里没有播放地址")
        info = item_to_info(item, aweme_id)
        dest = out_dir / "video.mp4"
        info.source_url = stream_to_file(urls, dest, self.session, self.timeout)
        info.video_path = dest
        info.backend = self.name
        return info
