from pathlib import Path

import pytest

from douyin_workflow.config import Settings
from douyin_workflow.downloaders import build_backends
from douyin_workflow.downloaders.base import DownloadError
from douyin_workflow.downloaders.browser import BrowserBackend


def test_browser_backend_rejects_missing_explicit_executable(tmp_path):
    backend = BrowserBackend(str(tmp_path / "missing-chrome"))
    with pytest.raises(DownloadError, match="可执行文件不存在"):
        backend.fetch_item("7685682624978832691")


def test_build_backends_passes_browser_settings(tmp_path):
    chrome = tmp_path / "chrome"
    chrome.write_text("binary", encoding="utf-8")
    [backend] = build_backends(Settings(backends=["browser"], chromium_executable=str(chrome)))
    assert isinstance(backend, BrowserBackend)
    assert backend.executable_path == str(chrome)


def test_browser_download_maps_item_and_uses_ephemeral_cookies(tmp_path, monkeypatch):
    item = {
        "aweme_id": "7685682624978832691",
        "desc": "标题",
        "author": {"nickname": "作者"},
        "video": {"duration": 136046, "play_addr": {"url_list": ["https://cdn.example/video.mp4"]}},
    }
    backend = BrowserBackend()
    monkeypatch.setattr(
        backend,
        "fetch_item",
        lambda aweme_id: (
            item,
            [{"name": "ttwid", "value": "anon", "domain": ".douyin.com", "path": "/"}],
            "UA",
        ),
    )

    def fake_stream(urls, dest, session, timeout, referer, user_agent):
        assert session.cookies.get("ttwid", domain=".douyin.com", path="/") == "anon"
        assert user_agent == "UA" and referer.endswith(item["aweme_id"])
        dest.write_bytes(b"video")
        return urls[0]

    monkeypatch.setattr("douyin_workflow.downloaders.browser.stream_to_file", fake_stream)
    info = backend.download("unused", item["aweme_id"], tmp_path)
    assert info.backend == "browser" and info.title == "标题" and info.duration_s == 136.0
    assert info.video_path == Path(tmp_path / "video.mp4")
