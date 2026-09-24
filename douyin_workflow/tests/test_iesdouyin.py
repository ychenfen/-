import json

import pytest
import requests

from douyin_workflow.downloaders import base
from douyin_workflow.downloaders.base import DownloadError, UnsupportedContent
from douyin_workflow.downloaders.iesdouyin import IesDouyinBackend, parse_share_page, play_urls

ITEM = {
    "aweme_id": "7372484719365098803",
    "desc": "美联储降息对A股意味着什么 #财经",
    "create_time": 1716600000,
    "author": {"nickname": "财经小王"},
    "statistics": {"digg_count": 12000},
    "video": {
        "duration": 61234,
        "play_addr": {
            "uri": "v0200fg10000abc",
            "url_list": ["https://aweme.snssdk.com/aweme/v1/playwm/?video_id=v0200fg10000abc&ratio=720p&line=0"],
        },
    },
}


def page(loader_data: dict) -> str:
    data = json.dumps({"loaderData": loader_data}, ensure_ascii=False)
    return f"<html><script>window._ROUTER_DATA = {data}</script></html>"


def test_parse_share_page_video():
    html = page({"video_(id)/page": {"videoInfoRes": {"item_list": [ITEM]}}})
    assert parse_share_page(html)["desc"].startswith("美联储")


def test_parse_share_page_note_key():
    html = page({"note_(id)/page": {"videoInfoRes": {"item_list": [ITEM]}}})
    assert parse_share_page(html)["aweme_id"] == ITEM["aweme_id"]


def test_parse_share_page_filtered():
    html = page({"video_(id)/page": {"videoInfoRes": {"item_list": [], "filter_list": [{"filter_reason": "deleted"}]}}})
    with pytest.raises(UnsupportedContent):
        parse_share_page(html)


def test_parse_share_page_layout_changed():
    with pytest.raises(DownloadError):
        parse_share_page("<html>nothing here</html>")


def test_play_urls_removes_watermark_and_adds_uri_fallback():
    urls = play_urls(ITEM)
    assert urls[0] == "https://aweme.snssdk.com/aweme/v1/play/?video_id=v0200fg10000abc&ratio=720p&line=0"
    assert urls[1].endswith("video_id=v0200fg10000abc&ratio=1080p&line=0")


class FakeResp:
    def __init__(self, text="", body=b"", ctype="video/mp4", status=200):
        self.text, self.body, self.status = text, body, status
        self.headers = {"Content-Type": ctype}

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(str(self.status))

    def iter_content(self, chunk_size):
        yield self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeSession:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, url, **k):
        self.calls.append(url)
        for prefix, resp in self.routes:
            if url.startswith(prefix):
                return resp
        raise requests.ConnectionError(url)


def test_backend_download_falls_back_across_cdn_urls(tmp_path):
    html = page({"video_(id)/page": {"videoInfoRes": {"item_list": [ITEM]}}})
    sess = FakeSession(
        [
            ("https://www.iesdouyin.com/share/video/", FakeResp(text=html, ctype="text/html")),
            # 第一个地址返回风控 HTML，第二个地址是真视频
            ("https://aweme.snssdk.com/aweme/v1/play/?video_id=v0200fg10000abc&ratio=720p", FakeResp(ctype="text/html")),
            ("https://aweme.snssdk.com/aweme/v1/play/?video_id=v0200fg10000abc&ratio=1080p", FakeResp(body=b"x" * (base.MIN_VIDEO_BYTES + 1))),
        ]
    )
    info = IesDouyinBackend(session=sess).download("u", ITEM["aweme_id"], tmp_path)
    assert info.video_path.read_bytes().startswith(b"x")
    assert info.title.startswith("美联储") and info.author == "财经小王" and info.duration_s == 61.2
    assert "ratio=1080p" in info.source_url
    assert not list(tmp_path.glob("*.part"))


def test_backend_rejects_tiny_file(tmp_path):
    html = page({"video_(id)/page": {"videoInfoRes": {"item_list": [ITEM]}}})
    sess = FakeSession(
        [
            ("https://www.iesdouyin.com/share/video/", FakeResp(text=html, ctype="text/html")),
            ("https://aweme.snssdk.com/", FakeResp(body=b"tiny")),
        ]
    )
    with pytest.raises(DownloadError, match="过小"):
        IesDouyinBackend(session=sess).download("u", ITEM["aweme_id"], tmp_path)


def test_backend_image_note_is_unsupported(tmp_path):
    note = {**ITEM, "images": [{"url_list": ["x"]}], "video": {"play_addr": {"url_list": []}}}
    html = page({"note_(id)/page": {"videoInfoRes": {"item_list": [note]}}})
    sess = FakeSession([("https://www.iesdouyin.com/share/video/", FakeResp(text=html, ctype="text/html"))])
    with pytest.raises(UnsupportedContent):
        IesDouyinBackend(session=sess).download("u", ITEM["aweme_id"], tmp_path)
