import hashlib
import json
import stat
import time
import zipfile

from douyin_workflow.config import Settings
from douyin_workflow.media import cleanup_retained_videos, create_workbench_bundle, retained_video


def make_item(tmp_path, aweme_id="7372484719365098803", video=b"video"):
    data = tmp_path / "data"
    item = data / aweme_id
    item.mkdir(parents=True)
    (item / "video.mp4").write_bytes(video)
    (item / "transcript.txt").write_text("原始逐字稿", encoding="utf-8")
    (item / "meta.json").write_text(
        json.dumps({"title": "标题", "author": "作者", "duration_s": 12.3, "share_url": "https://v.douyin.com/x/"}),
        encoding="utf-8",
    )
    return Settings(data_dir=data, keep_video=True), item


def test_retained_video_rejects_bad_id(tmp_path):
    settings, _ = make_item(tmp_path)
    assert retained_video(settings, "../../etc") is None
    assert retained_video(settings, "7372484719365098803").name == "video.mp4"


def test_bundle_is_private_sanitized_and_verified(tmp_path):
    settings, item = make_item(tmp_path)
    bundle = create_workbench_bundle(settings, item.name, "校对后的逐字稿")
    try:
        assert stat.S_IMODE(bundle.stat().st_mode) == 0o600
        with zipfile.ZipFile(bundle) as archive:
            assert set(archive.namelist()) == {"video.mp4", "transcript.txt", "manifest.json"}
            manifest = json.loads(archive.read("manifest.json"))
            assert manifest["rights"]["status"] == "unverified"
            assert "dir" not in manifest and "backend" not in manifest
            text = archive.read("transcript.txt")
            assert text.decode().strip() == "校对后的逐字稿"
            assert manifest["sha256"]["transcript"] == hashlib.sha256(text).hexdigest()
    finally:
        bundle.unlink(missing_ok=True)


def test_cleanup_applies_ttl_without_deleting_transcript(tmp_path):
    settings, item = make_item(tmp_path)
    old = time.time() - 48 * 3600
    (item / "video.mp4").touch()
    import os

    os.utime(item / "video.mp4", (old, old))
    settings.video_ttl_hours = 24
    removed = cleanup_retained_videos(settings)
    assert removed and not (item / "video.mp4").exists()
    assert (item / "transcript.txt").exists() and (item / "meta.json").exists()
