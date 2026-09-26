import pytest

from douyin_workflow import share

SHARE_TEXT = (
    "7.43 复制打开抖音，看看【财经小王的作品】美联储降息对A股意味着什么 # 财经 "
    "https://v.douyin.com/iRNBho6u/ S@y.Ec 03/12 HVl:/"
)


def test_extract_url_from_share_text():
    assert share.extract_url(SHARE_TEXT) == "https://v.douyin.com/iRNBho6u/"


def test_extract_url_strips_chinese_punctuation():
    assert share.extract_url("看这个https://v.douyin.com/abc123/，很不错") == "https://v.douyin.com/abc123/"


def test_extract_url_rejects_non_douyin():
    with pytest.raises(share.ShareParseError):
        share.extract_url("https://example.com/video/123456789012")


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.douyin.com/video/7372484719365098803", "7372484719365098803"),
        ("https://www.iesdouyin.com/share/video/7372484719365098803/?region=CN", "7372484719365098803"),
        ("https://www.douyin.com/note/7372484719365098803", "7372484719365098803"),
        ("https://www.douyin.com/discover?modal_id=7372484719365098803", "7372484719365098803"),
        ("https://v.douyin.com/iRNBho6u/", None),
    ],
)
def test_extract_aweme_id(url, expected):
    assert share.extract_aweme_id(url) == expected


def test_resolve_long_url_needs_no_network():
    class Boom:
        def get(self, *a, **k):
            raise AssertionError("不该发请求")

    assert share.resolve("https://www.douyin.com/video/7372484719365098803", session=Boom()) == (
        "https://www.douyin.com/video/7372484719365098803",
        "7372484719365098803",
    )


def test_resolve_short_url_follows_redirect():
    class Resp:
        url = "https://www.iesdouyin.com/share/video/7372484719365098803/?region=CN&mid=1"
        history = []

    class Sess:
        def get(self, url, **k):
            assert url == "https://v.douyin.com/iRNBho6u/"
            return Resp()

    url, aweme_id = share.resolve(SHARE_TEXT, session=Sess())
    assert aweme_id == "7372484719365098803"
