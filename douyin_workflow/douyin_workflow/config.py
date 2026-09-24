"""配置：全部走环境变量，便于 MCP 客户端在 env 里传入。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_list(name: str, default: str) -> list[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


@dataclass
class Settings:
    # 素材落盘目录：每条视频一个子目录 <data_dir>/<aweme_id>/
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("DOUYIN_DATA_DIR", "~/douyin_workflow_data")).expanduser()
    )
    # 下载后端顺序，前一个失败自动换下一个
    backends: list[str] = field(default_factory=lambda: _env_list("DOUYIN_BACKENDS", "iesdouyin,f2,ytdlp"))
    # Netscape 格式 cookies.txt（yt-dlp 用）；也可以用 DOUYIN_COOKIES_FROM_BROWSER=chrome
    cookies_file: str | None = field(default_factory=lambda: os.getenv("DOUYIN_COOKIES_FILE") or None)
    cookies_from_browser: str | None = field(
        default_factory=lambda: os.getenv("DOUYIN_COOKIES_FROM_BROWSER") or None
    )
    # 原始 cookie 字符串（f2 用），从浏览器开发者工具里复制
    cookie_string: str | None = field(default_factory=lambda: os.getenv("DOUYIN_COOKIE") or None)
    # 两次下载之间的最小间隔（秒），防风控
    min_interval: float = field(default_factory=lambda: float(os.getenv("DOUYIN_MIN_INTERVAL", "8")))
    # 转写模型：paraformer-zh 或 SenseVoiceSmall
    asr_model: str = field(default_factory=lambda: os.getenv("DOUYIN_ASR_MODEL", "paraformer-zh"))
    # auto / cuda / cuda:0 / cpu
    asr_device: str = field(default_factory=lambda: os.getenv("DOUYIN_ASR_DEVICE", "auto"))
    # 转写完是否保留视频文件（默认只留音频和文字）
    keep_video: bool = field(default_factory=lambda: os.getenv("DOUYIN_KEEP_VIDEO", "0") == "1")
    timeout: float = field(default_factory=lambda: float(os.getenv("DOUYIN_HTTP_TIMEOUT", "20")))


def get_settings() -> Settings:
    return Settings()
