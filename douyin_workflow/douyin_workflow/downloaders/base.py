from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

import requests

from ..share import MOBILE_UA


@dataclass
class VideoInfo:
    aweme_id: str
    title: str = ""
    author: str = ""
    duration_s: float | None = None
    video_path: Path | None = None
    source_url: str = ""
    backend: str = ""
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["video_path"] = str(self.video_path) if self.video_path else None
        return d


class DownloadError(RuntimeError):
    """单个后端失败，链条会继续尝试下一个后端。"""


class UnsupportedContent(RuntimeError):
    """内容本身不能处理（图文、已删除、私密），换后端也没用，链条直接停。"""


class Backend(Protocol):
    name: str

    def download(self, url: str, aweme_id: str, out_dir: Path) -> VideoInfo: ...


MIN_VIDEO_BYTES = 50 * 1024


def stream_to_file(
    urls: list[str], dest: Path, session: requests.Session, timeout: float, referer: str = "https://www.douyin.com/"
) -> str:
    """依次尝试多个 CDN 地址，返回成功的那个。太小的文件视为失败（多半是风控页）。"""
    errors = []
    tmp = dest.with_suffix(dest.suffix + ".part")
    for u in urls:
        try:
            with session.get(
                u, headers={"User-Agent": MOBILE_UA, "Referer": referer}, stream=True, timeout=timeout
            ) as r:
                r.raise_for_status()
                ctype = r.headers.get("Content-Type", "")
                if "text/html" in ctype or "json" in ctype:
                    raise DownloadError(f"返回的不是视频：{ctype}")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 16):
                        f.write(chunk)
            if tmp.stat().st_size < MIN_VIDEO_BYTES:
                raise DownloadError(f"文件过小（{tmp.stat().st_size} B），可能被风控")
            tmp.replace(dest)
            return u
        except (requests.RequestException, DownloadError, OSError) as e:
            errors.append(f"{u[:80]}: {e}")
            tmp.unlink(missing_ok=True)
    raise DownloadError("所有播放地址都失败：" + " | ".join(errors))
