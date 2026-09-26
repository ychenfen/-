import pytest

pytest.importorskip("mcp")

from douyin_workflow import mcp_server  # noqa: E402
from douyin_workflow.downloaders import AllBackendsFailed  # noqa: E402


def test_bad_share_text_returns_error():
    assert mcp_server.douyin_to_text("随便一段话")["error"] == "bad_share_text"


def test_download_failure_is_reported_not_raised(monkeypatch):
    def boom(*a, **k):
        raise AllBackendsFailed({"iesdouyin": "x", "ytdlp": "cookie 过期"})

    monkeypatch.setattr(mcp_server.pipeline, "douyin_to_text", boom)
    res = mcp_server.douyin_to_text("https://www.douyin.com/video/7372484719365098803")
    assert res["error"] == "download_failed" and res["backends"]["ytdlp"] == "cookie 过期"
