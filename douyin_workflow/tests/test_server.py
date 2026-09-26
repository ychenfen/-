import json
import threading
import urllib.error
import urllib.request

import pytest

from douyin_workflow import pipeline
from douyin_workflow.config import Settings
from douyin_workflow.server import App, make_server
from douyin_workflow.share import ShareParseError

AWEME = "7372484719365098803"
TOKEN = "t0ken"


@pytest.fixture
def serve(tmp_path):
    servers = []

    def start(runner, wait_s=2):
        settings = Settings(data_dir=tmp_path / "data")

        def resolver(text):
            if "douyin" not in text:
                raise ShareParseError("没有链接")
            return f"https://www.douyin.com/video/{AWEME}", AWEME

        srv = make_server(App(TOKEN, settings, runner=runner, resolver=resolver, wait_s=wait_s), "127.0.0.1", 0)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        servers.append(srv)
        return f"http://127.0.0.1:{srv.server_address[1]}", settings

    yield start
    for s in servers:
        s.shutdown()


def post(base, text, token=TOKEN, raw=False):
    body = text.encode() if raw else json.dumps({"text": text}).encode()
    req = urllib.request.Request(f"{base}/transcribe", data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


SHARE = "看看 https://v.douyin.com/abc/ 这个"


def ok_runner(url):
    return {
        "title": "降息怎么看",
        "author": "财经小王",
        "duration_s": 61.2,
        "transcript": "大家好。",
        "backend": "iesdouyin",
        "timing_s": {"download": 1.2, "transcribe": 3.4},
    }


def test_rejects_wrong_token(serve):
    base, _ = serve(ok_runner)
    with pytest.raises(urllib.error.HTTPError) as ei:
        post(base, SHARE, token="bad")
    assert ei.value.code == 401


def test_done_returns_readable_text(serve):
    base, _ = serve(ok_runner)
    res = post(base, SHARE)
    assert res["status"] == "done"
    assert res["text"] == "降息怎么看\n财经小王 · 61.2秒\n\n大家好。"


def test_done_also_returns_structured_fields(serve):
    base, _ = serve(ok_runner)
    res = post(base, SHARE)
    assert res == {
        "status": "done",
        "text": "降息怎么看\n财经小王 · 61.2秒\n\n大家好。",
        "aweme_id": AWEME,
        "cached": False,
        "title": "降息怎么看",
        "author": "财经小王",
        "duration_s": 61.2,
        "transcript": "大家好。",
        "backend": "iesdouyin",
        "timing_s": {"download": 1.2, "transcribe": 3.4},
        "video_available": False,
    }


def test_plain_text_body_accepted(serve):
    base, _ = serve(ok_runner)
    assert post(base, SHARE, raw=True)["status"] == "done"


def test_bad_share_text(serve):
    base, _ = serve(ok_runner)
    res = post(base, "随便一段话")
    assert res["status"] == "error" and "没认出" in res["text"]


def test_running_then_done_without_duplicate_work(serve):
    gate, calls = threading.Event(), []

    def slow(url):
        calls.append(url)
        gate.wait(5)
        return ok_runner(url)

    base, _ = serve(slow, wait_s=0.2)
    assert post(base, SHARE)["status"] == "running"
    assert post(base, SHARE)["status"] == "running"  # 重发不会重新开任务
    gate.set()
    assert post(base, SHARE)["status"] == "done"
    assert len(calls) == 1


def test_cached_result_served_from_disk(serve):
    base, settings = serve(lambda url: pytest.fail("不该再跑"))
    d = settings.data_dir / AWEME
    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps({"title": "旧的", "author": "a", "duration_s": 3}), encoding="utf-8")
    (d / "transcript.txt").write_text("缓存里的字", encoding="utf-8")
    res = post(base, SHARE)
    assert res["status"] == "done" and res["cached"] is True and "缓存里的字" in res["text"]
    assert res["title"] == "旧的" and res["transcript"] == "缓存里的字"


def test_authenticated_video_and_bundle_download(serve):
    base, settings = serve(lambda url: pytest.fail("不该再跑"))
    d = settings.data_dir / AWEME
    d.mkdir(parents=True)
    (d / "video.mp4").write_bytes(b"video-bytes")
    (d / "meta.json").write_text(
        json.dumps({"title": "旧的", "author": "a", "duration_s": 3, "share_url": "https://v.douyin.com/x/"}),
        encoding="utf-8",
    )
    (d / "transcript.txt").write_text("缓存里的字", encoding="utf-8")
    assert post(base, SHARE)["video_available"] is True

    request = urllib.request.Request(f"{base}/media/{AWEME}/video")
    request.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(request) as response:
        assert response.read() == b"video-bytes"
        assert response.headers["Cache-Control"] == "private, no-store"

    body = json.dumps({"aweme_id": AWEME, "transcript": "校对稿"}).encode()
    request = urllib.request.Request(f"{base}/bundle", data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(request) as response:
        import io
        import zipfile

        with zipfile.ZipFile(io.BytesIO(response.read())) as archive:
            assert archive.read("transcript.txt").decode().strip() == "校对稿"
            assert archive.read("video.mp4") == b"video-bytes"


def test_error_is_reported_and_retry_restarts(serve):
    calls = []

    def flaky(url):
        calls.append(1)
        if len(calls) == 1:
            return {"error": "download_failed", "message": "cookie 过期"}
        return ok_runner(url)

    base, _ = serve(flaky)
    first = post(base, SHARE)
    assert first["status"] == "error" and "cookie 过期" in first["text"]
    assert post(base, SHARE)["status"] == "done"


def test_run_safe_maps_errors(monkeypatch):
    def boom(*a, **k):
        raise ShareParseError("x")

    monkeypatch.setattr(pipeline, "douyin_to_text", boom)
    assert pipeline.run_safe("x")["error"] == "bad_share_text"


def test_index_page_served():
    import threading
    import urllib.request

    from douyin_workflow.server import App, make_server

    app = App("t", runner=lambda url: {}, resolver=lambda t: ("u", "1"))
    srv = make_server(app, "127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as response:
            body = response.read().decode("utf-8")
            assert "default-src 'none'" in response.headers["Content-Security-Policy"]
            assert response.headers["X-Frame-Options"] == "DENY"
            assert "__CSP_NONCE__" not in body
        assert "抖音素材台" in body and 'fetch("transcribe"' in body
        assert all(
            label in body
            for label in ("复制纯逐字稿", "下载 TXT", "下载原视频", "下载工作台素材包", "复制一键成片提示词", "最近处理")
        )

        req = urllib.request.Request(f"http://127.0.0.1:{port}/", method="HEAD")
        with urllib.request.urlopen(req) as response:
            assert response.status == 200
            assert response.headers["Content-Type"] == "text/html; charset=utf-8"
            assert int(response.headers["Content-Length"]) == len(body.encode("utf-8"))
            assert response.read() == b""
    finally:
        srv.shutdown()
