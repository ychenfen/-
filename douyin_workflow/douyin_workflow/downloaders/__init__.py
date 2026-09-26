"""多后端下载链：按顺序尝试，前一个失败自动降级到下一个。"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from ..config import Settings
from .base import Backend, DownloadError, UnsupportedContent, VideoInfo
from .browser import BrowserBackend
from .f2_backend import F2Backend
from .iesdouyin import IesDouyinBackend
from .ytdlp_backend import YtDlpBackend

log = logging.getLogger(__name__)

__all__ = [
    "AllBackendsFailed",
    "DownloadChain",
    "DownloadError",
    "UnsupportedContent",
    "VideoInfo",
    "build_backends",
]


class AllBackendsFailed(RuntimeError):
    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        detail = "; ".join(f"[{k}] {v}" for k, v in errors.items())
        super().__init__(f"所有下载后端都失败了：{detail}")


def build_backends(settings: Settings) -> list[Backend]:
    factories = {
        "browser": lambda: BrowserBackend(settings.chromium_executable, timeout=settings.timeout),
        "iesdouyin": lambda: IesDouyinBackend(timeout=settings.timeout),
        "f2": lambda: F2Backend(cookie=settings.cookie_string, timeout=settings.timeout),
        "ytdlp": lambda: YtDlpBackend(settings.cookies_file, settings.cookies_from_browser),
    }
    unknown = [b for b in settings.backends if b not in factories]
    if unknown:
        raise ValueError(f"未知后端：{unknown}，可选 {list(factories)}")
    return [factories[b]() for b in settings.backends]


class DownloadChain:
    def __init__(self, backends: list[Backend], min_interval: float = 0):
        self.backends = backends
        self.min_interval = min_interval
        self._last = float("-inf")
        self._lock = threading.Lock()

    def _throttle(self) -> None:
        with self._lock:
            wait = self._last + self.min_interval - time.monotonic()
            if wait > 0:
                log.info("限速：等待 %.1fs", wait)
                time.sleep(wait)
            self._last = time.monotonic()

    def download(self, url: str, aweme_id: str, out_dir: Path) -> tuple[VideoInfo, dict[str, str]]:
        """返回 (结果, 前面失败的后端及原因)。失败原因也返回，方便发现"首选后端已经坏了"。"""
        out_dir.mkdir(parents=True, exist_ok=True)
        errors: dict[str, str] = {}
        for backend in self.backends:
            self._throttle()
            try:
                info = backend.download(url, aweme_id, out_dir)
                log.info("[%s] 下载成功 %s", backend.name, aweme_id)
                return info, errors
            except UnsupportedContent:
                raise
            except DownloadError as e:
                log.warning("[%s] 失败，降级：%s", backend.name, e)
                errors[backend.name] = str(e)
            except Exception as e:  # 后端里的意外异常也不能拖垮整条链
                log.exception("[%s] 意外异常", backend.name)
                errors[backend.name] = f"{type(e).__name__}: {e}"
        raise AllBackendsFailed(errors)
