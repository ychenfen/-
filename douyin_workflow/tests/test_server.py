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
    return {"title": "降息怎么看", "author": "财经小王", "duration_s": 61.2, "transcript": "大家好。"}


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
