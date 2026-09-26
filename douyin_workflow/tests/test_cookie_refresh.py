import stat

import pytest

from douyin_workflow.cookie_refresh import (
    CookieRefreshError,
    netscape_cookie_text,
    refresh,
    wait_for_required_cookies,
    write_cookie_jar,
)


COOKIES = [
    {
        "domain": "www.douyin.com",
        "path": "/",
        "name": "s_v_web_id",
        "value": "anonymous-verify-id",
        "expires": 2_000_000_000,
        "secure": False,
        "httpOnly": False,
    },
    {
        "domain": ".douyin.com",
        "path": "/",
        "name": "ttwid",
        "value": "anonymous-device-id",
        "expires": 2_000_000_000,
        "secure": True,
        "httpOnly": True,
    },
    {
        "domain": "www.douyin.com",
        "path": "/",
        "name": "UIFID",
        "value": "anonymous-ui-id",
        "expires": 2_000_000_000,
        "secure": True,
        "httpOnly": False,
    },
    {
        "domain": "example.com",
        "path": "/",
        "name": "must-not-leak",
        "value": "other-site-cookie",
        "expires": 0,
        "secure": False,
        "httpOnly": False,
    },
]


def test_netscape_cookie_text_keeps_only_anonymous_douyin_cookies():
    text = netscape_cookie_text(COOKIES)
    assert "s_v_web_id" in text and "ttwid" in text and "UIFID" in text
    assert "#HttpOnly_.douyin.com" in text
    assert "example.com" not in text and "other-site-cookie" not in text


def test_netscape_cookie_text_normalizes_session_expiry_without_value_warning():
    cookies = [dict(cookie) for cookie in COOKIES]
    cookies[0]["expires"] = -1
    text = netscape_cookie_text(cookies)
    row = next(line for line in text.splitlines() if "\ts_v_web_id\t" in line)
    assert row.split("\t")[4] == "0"


def test_netscape_cookie_text_requires_security_cookies():
    with pytest.raises(CookieRefreshError, match="必要 Cookie"):
        netscape_cookie_text(COOKIES[:1])


def test_netscape_cookie_text_rejects_login_cookie():
    with pytest.raises(CookieRefreshError, match="登录 Cookie"):
        netscape_cookie_text([*COOKIES, {"domain": ".douyin.com", "name": "sessionid", "value": "secret"}])


def test_wait_for_required_cookies_allows_async_set_cookie():
    snapshots = [COOKIES[:1], COOKIES]

    class Context:
        def cookies(self):
            return snapshots.pop(0) if len(snapshots) > 1 else snapshots[0]

    class Page:
        waits = 0

        def wait_for_timeout(self, delay):
            self.waits += 1

    page = Page()
    assert wait_for_required_cookies(Context(), page, 1000) == COOKIES
    assert page.waits == 1


def test_write_cookie_jar_is_atomic_and_private(tmp_path):
    output = tmp_path / "private" / "cookies.txt"
    write_cookie_jar(output, netscape_cookie_text(COOKIES))
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert stat.S_IMODE(output.parent.stat().st_mode) == 0o700
    assert not list(output.parent.glob(".cookies.txt.*"))


def test_write_cookie_jar_refuses_symlink(tmp_path):
    target = tmp_path / "target"
    target.write_text("keep", encoding="utf-8")
    link = tmp_path / "cookies.txt"
    link.symlink_to(target)
    with pytest.raises(CookieRefreshError, match="符号链接"):
        write_cookie_jar(link, netscape_cookie_text(COOKIES))
    assert target.read_text(encoding="utf-8") == "keep"


def test_write_cookie_jar_refuses_public_directory(tmp_path):
    public = tmp_path / "public"
    public.mkdir(mode=0o755)
    with pytest.raises(CookieRefreshError, match="目录权限过宽"):
        write_cookie_jar(public / "cookies.txt", netscape_cookie_text(COOKIES))


def test_refresh_rejects_missing_explicit_browser_before_launch(tmp_path):
    with pytest.raises(CookieRefreshError, match="可执行文件不存在"):
        refresh(tmp_path / "cookies.txt", "https://www.douyin.com/video/123", executable_path="/missing/chrome")
