import json
from dataclasses import replace

import pytest

from douyin_workflow import cli, pipeline
from douyin_workflow.config import Settings
from douyin_workflow.downloaders import AllBackendsFailed, DownloadChain, DownloadError, UnsupportedContent, VideoInfo

AWEME = "7372484719365098803"
URL = f"https://www.douyin.com/video/{AWEME}"


class Fake:
    def __init__(self, name, exc=None):
        self.name, self.exc, self.calls = name, exc, 0

    def download(self, url, aweme_id, out_dir):
        self.calls += 1
        if self.exc:
            raise self.exc
        p = out_dir / "video.mp4"
        p.write_bytes(b"v")
        return VideoInfo(aweme_id=aweme_id, title="标题", author="作者", duration_s=10.0, video_path=p, backend=self.name)


def test_chain_falls_back_and_reports_errors(tmp_path):
    a, b, c = Fake("a", DownloadError("签名变了")), Fake("b", ValueError("bug")), Fake("c")
    info, errors = DownloadChain([a, b, c]).download(URL, AWEME, tmp_path)
    assert info.backend == "c"
    assert errors == {"a": "签名变了", "b": "ValueError: bug"}


def test_chain_all_failed(tmp_path):
    with pytest.raises(AllBackendsFailed) as ei:
        DownloadChain([Fake("a", DownloadError("x")), Fake("b", DownloadError("y"))]).download(URL, AWEME, tmp_path)
    assert set(ei.value.errors) == {"a", "b"}


def test_chain_stops_on_unsupported_content(tmp_path):
    b = Fake("b")
    with pytest.raises(UnsupportedContent):
        DownloadChain([Fake("a", UnsupportedContent("图文")), b]).download(URL, AWEME, tmp_path)
    assert b.calls == 0


def test_chain_throttles(monkeypatch, tmp_path):
    sleeps = []
    monkeypatch.setattr("douyin_workflow.downloaders.time.sleep", sleeps.append)
    chain = DownloadChain([Fake("a")], min_interval=5)
    chain.download(URL, AWEME, tmp_path)
    assert sleeps == []
    chain.download(URL, AWEME, tmp_path)
    assert len(sleeps) == 1 and 0 < sleeps[0] <= 5


@pytest.fixture
def settings(tmp_path, monkeypatch):
    s = Settings(data_dir=tmp_path / "data", backends=["iesdouyin"], min_interval=0)
    fake = Fake("fake")
    monkeypatch.setattr(pipeline, "_chain", DownloadChain([fake]))
    monkeypatch.setattr(pipeline, "extract_audio", lambda v, w: w.write_bytes(b"wav") or w)
    monkeypatch.setattr(pipeline, "transcribe", lambda w, m, d: "大家好，今天聊聊降息。")
    s.fake = fake
    return s


def test_pipeline_writes_files_and_uses_cache(settings):
    res = pipeline.douyin_to_text(URL, settings=settings)
    item = settings.data_dir / AWEME
    assert res["transcript"] == "大家好，今天聊聊降息。" and res["cached"] is False
    assert (item / "transcript.txt").read_text(encoding="utf-8") == res["transcript"]
    assert json.loads((item / "meta.json").read_text(encoding="utf-8"))["title"] == "标题"
    assert not (item / "video.mp4").exists()  # 默认不保留视频

    again = pipeline.douyin_to_text(URL, settings=settings)
    assert again["cached"] is True and settings.fake.calls == 1

    pipeline.douyin_to_text(URL, force=True, settings=settings)
    assert settings.fake.calls == 2


def test_pipeline_keep_video(settings):
    pipeline.douyin_to_text(URL, settings=replace(settings, keep_video=True))
    assert (settings.data_dir / AWEME / "video.mp4").exists()


def test_list_local(settings):
    pipeline.douyin_to_text(URL, settings=settings)
    [m] = pipeline.list_local(settings=settings)
    assert m["aweme_id"] == AWEME and "transcript" not in m


def test_healthcheck_exit_codes(monkeypatch):
    monkeypatch.setenv("DOUYIN_HEALTH_URLS", URL)
    monkeypatch.setenv("DOUYIN_BACKENDS", "iesdouyin,ytdlp")
    sent = []
    monkeypatch.setattr(cli, "notify", lambda t, b: sent.append(t))

    def fake_build(s):
        return [Fake(s.backends[0], DownloadError("坏了") if s.backends[0] == "iesdouyin" else None)]

    monkeypatch.setattr(cli, "build_backends", fake_build)
    assert cli.main(["healthcheck"]) == 1
    assert "iesdouyin" in sent[0]

    monkeypatch.setattr(cli, "build_backends", lambda s: [Fake(s.backends[0], DownloadError("x"))])
    assert cli.main(["healthcheck"]) == 2

    monkeypatch.setattr(cli, "build_backends", lambda s: [Fake(s.backends[0])])
    assert cli.main(["healthcheck"]) == 0


def test_f2_backend_maps_filter_and_wraps_errors(monkeypatch, tmp_path):
    from douyin_workflow.downloaders import f2_backend

    class Filt:
        aweme_id, desc_raw, nickname_raw, duration = AWEME, "标题", "作者", 30500
        video_play_addr = ["https://cdn/1.mp4"]

    async def fetch_ok(self, aweme_id):
        return Filt()

    monkeypatch.setitem(__import__("sys").modules, "f2", type(__import__("sys"))("f2"))
    monkeypatch.setattr(f2_backend.F2Backend, "_fetch", fetch_ok)
    monkeypatch.setattr(f2_backend, "stream_to_file", lambda urls, dest, s, t: urls[0])
    info = f2_backend.F2Backend(cookie="c").download(URL, AWEME, tmp_path)
    assert (info.title, info.author, info.duration_s, info.backend) == ("标题", "作者", 30.5, "f2")

    async def fetch_bad(self, aweme_id):
        raise RuntimeError("a_bogus 失效")

    monkeypatch.setattr(f2_backend.F2Backend, "_fetch", fetch_bad)
    with pytest.raises(DownloadError, match="a_bogus"):
        f2_backend.F2Backend(cookie="c").download(URL, AWEME, tmp_path)
    with pytest.raises(DownloadError, match="DOUYIN_COOKIE"):
        f2_backend.F2Backend(cookie=None).download(URL, AWEME, tmp_path)
