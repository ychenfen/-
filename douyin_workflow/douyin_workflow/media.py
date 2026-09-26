"""Private media downloads, workbench bundles, and bounded video retention."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import zipfile
from pathlib import Path

from .config import Settings


AWEME_RE = re.compile(r"^[0-9]{10,25}$")


def retained_video(settings: Settings, aweme_id: str) -> Path | None:
    if not AWEME_RE.fullmatch(aweme_id):
        return None
    item_dir = settings.data_dir / aweme_id
    candidates = sorted(item_dir.glob("video.*"))
    for path in candidates:
        if path.is_file() and path.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}:
            return path
    return None


def cleanup_retained_videos(settings: Settings, now: float | None = None) -> list[Path]:
    """Delete only retained source videos, first by TTL and then by total quota."""
    now = now if now is not None else time.time()
    ttl_seconds = max(0.0, settings.video_ttl_hours) * 3600
    videos = [path for path in settings.data_dir.glob("*/video.*") if path.is_file()]
    removed: list[Path] = []
    kept: list[Path] = []
    for path in videos:
        if ttl_seconds and now - path.stat().st_mtime > ttl_seconds:
            path.unlink(missing_ok=True)
            removed.append(path)
        else:
            kept.append(path)

    quota = max(0, settings.video_max_bytes)
    total = sum(path.stat().st_size for path in kept if path.exists())
    for path in sorted(kept, key=lambda candidate: candidate.stat().st_mtime):
        if total <= quota:
            break
        size = path.stat().st_size
        path.unlink(missing_ok=True)
        total -= size
        removed.append(path)
    return removed


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_workbench_bundle(settings: Settings, aweme_id: str, transcript: str | None = None) -> Path:
    video = retained_video(settings, aweme_id)
    if video is None:
        raise FileNotFoundError("原视频未保留或已经超过保留期限")
    item_dir = settings.data_dir / aweme_id
    meta_path = item_dir / "meta.json"
    transcript_path = item_dir / "transcript.txt"
    if not meta_path.is_file() or not transcript_path.is_file():
        raise FileNotFoundError("素材元数据不完整")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    text = transcript if transcript is not None else transcript_path.read_text(encoding="utf-8")
    if len(text.encode("utf-8")) > 512 * 1024:
        raise ValueError("逐字稿过长")
    transcript_bytes = (text + ("" if text.endswith("\n") else "\n")).encode("utf-8")

    manifest = {
        "schema": "dy2text-workbench-bundle/v1",
        "aweme_id": aweme_id,
        "title": meta.get("title") or "",
        "author": meta.get("author") or "",
        "duration_s": meta.get("duration_s"),
        "source_url": meta.get("share_url") or "",
        "source_platform": "douyin",
        "video_file": "video" + video.suffix.lower(),
        "transcript_file": "transcript.txt",
        "sha256": {"video": _sha256(video), "transcript": hashlib.sha256(transcript_bytes).hexdigest()},
        "rights": {
            "status": "unverified",
            "intended_use": "private-research-material",
            "note": "下载不等于获得发布授权；公开使用前必须单独核验版权、肖像和平台规则。",
        },
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    fd, name = tempfile.mkstemp(prefix=f"dy2text-{aweme_id}-", suffix=".zip")
    os.close(fd)
    bundle = Path(name)
    bundle.chmod(0o600)
    try:
        with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.write(video, manifest["video_file"])
            archive.writestr("transcript.txt", transcript_bytes)
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        return bundle
    except Exception:
        bundle.unlink(missing_ok=True)
        raise
