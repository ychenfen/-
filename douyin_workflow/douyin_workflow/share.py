"""分享口令解析：从一段复制来的口令里找出链接，跟随短链跳转拿到作品 ID。"""

from __future__ import annotations

import re

import requests

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)

_URL_RE = re.compile(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+")
# /video/123、/note/123、/share/video/123、?modal_id=123、?aweme_id=123
_ID_RES = [
    re.compile(r"/(?:share/)?(?:video|note|slides)/(\d{8,})"),
    re.compile(r"[?&](?:modal_id|aweme_id|item_id)=(\d{8,})"),
]


class ShareParseError(ValueError):
    pass


def extract_url(share_text: str) -> str:
    """从口令文本里取第一个 douyin 链接，例如
    '7.43 复制打开抖音，看看【xx的作品】… https://v.douyin.com/iRNBho6u/ S@y.Ec 03/12'
    """
    for m in _URL_RE.finditer(share_text):
        url = m.group(0).rstrip(".,，。)）】」")
        if "douyin.com" in url or "iesdouyin.com" in url:
            return url
    raise ShareParseError(f"没有在口令里找到抖音链接：{share_text[:80]!r}")


def extract_aweme_id(url: str) -> str | None:
    for r in _ID_RES:
        m = r.search(url)
        if m:
            return m.group(1)
    return None


def resolve(share_text: str, session: requests.Session | None = None, timeout: float = 20) -> tuple[str, str]:
    """返回 (最终 URL, aweme_id)。长链直接解析，短链 v.douyin.com 跟随 302。"""
    url = extract_url(share_text)
    aweme_id = extract_aweme_id(url)
    if aweme_id:
        return url, aweme_id

    s = session or requests.Session()
    resp = s.get(url, headers={"User-Agent": MOBILE_UA}, allow_redirects=True, timeout=timeout)
    candidates = [resp.url] + [r.headers.get("Location", "") for r in resp.history]
    for c in candidates:
        aweme_id = extract_aweme_id(c)
        if aweme_id:
            return resp.url, aweme_id
    raise ShareParseError(f"短链跳转后没拿到作品 ID：{url} -> {resp.url}")
