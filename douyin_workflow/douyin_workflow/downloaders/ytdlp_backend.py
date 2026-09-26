"""后端 3：yt-dlp 的 Douyin 提取器。维护活跃但基本必须带 cookies。"""

from __future__ import annotations

from pathlib import Path

from .base import DownloadError, VideoInfo


class YtDlpBackend:
    name = "ytdlp"

    def __init__(self, cookies_file: str | None = None, cookies_from_browser: str | None = None):
        self.cookies_file = cookies_file
        self.cookies_from_browser = cookies_from_browser

    def download(self, url: str, aweme_id: str, out_dir: Path) -> VideoInfo:
        try:
            import yt_dlp
        except ImportError as e:
            raise DownloadError("未安装 yt-dlp（pip install yt-dlp）") from e

        opts = {
            "outtmpl": str(out_dir / "video.%(ext)s"),
            "format": "best[ext=mp4]/best",
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "overwrites": True,
            # MCP 走 stdio，yt-dlp 不能往 stdout 打东西
            "logger": _QuietLogger(),
        }
        if self.cookies_file:
            opts["cookiefile"] = self.cookies_file
        if self.cookies_from_browser:
            opts["cookiesfrombrowser"] = (self.cookies_from_browser,)

        # 统一喂标准长链，yt-dlp 的 DouyinIE 匹配这个格式
        target = f"https://www.douyin.com/video/{aweme_id}"
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                meta = ydl.extract_info(target, download=True)
                path = Path(ydl.prepare_filename(meta))
        except Exception as e:
            raise DownloadError(f"yt-dlp 失败：{e}") from e
        if not path.exists():
            raise DownloadError(f"yt-dlp 报告成功但找不到文件：{path}")

        return VideoInfo(
            aweme_id=aweme_id,
            title=(meta.get("description") or meta.get("title") or "").strip(),
            author=(meta.get("uploader") or meta.get("channel") or "").strip(),
            duration_s=meta.get("duration"),
            video_path=path,
            source_url=meta.get("webpage_url") or target,
            backend=self.name,
        )


class _QuietLogger:
    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass
