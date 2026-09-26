"""Refresh a yt-dlp cookie jar from an isolated, anonymous browser session.

This deliberately never opens a persistent browser profile.  The resulting
cookie jar therefore contains no user login session and can safely be kept on
the server with mode 0600.
"""

from __future__ import annotations

import argparse
import os
import stat
import tempfile
import time
from pathlib import Path


DEFAULT_SEED_URL = "https://www.douyin.com/video/7685682624978832691"
REQUIRED_COOKIES = {"s_v_web_id", "ttwid", "UIFID"}
LOGIN_COOKIE_NAMES = {"sessionid", "sessionid_ss", "sid_guard", "sid_tt", "uid_tt", "uid_tt_ss"}


class CookieRefreshError(RuntimeError):
    pass


def _is_douyin_cookie(cookie: dict) -> bool:
    domain = str(cookie.get("domain") or "").lstrip(".").lower()
    name = str(cookie.get("name") or "")
    return bool(name) and (domain == "douyin.com" or domain.endswith(".douyin.com"))


def netscape_cookie_text(cookies: list[dict]) -> str:
    """Serialize only douyin.com cookies without logging any values."""
    selected = [cookie for cookie in cookies if _is_douyin_cookie(cookie)]
    names = {str(cookie["name"]) for cookie in selected}
    if names & LOGIN_COOKIE_NAMES:
        raise CookieRefreshError("匿名浏览器意外出现登录 Cookie，拒绝写入")
    missing = REQUIRED_COOKIES - names
    if missing:
        raise CookieRefreshError("匿名浏览器没有拿到必要 Cookie，可能遇到风控或页面改版")

    lines = ["# Netscape HTTP Cookie File", "# Generated from an isolated anonymous browser session."]
    for cookie in sorted(selected, key=lambda value: (str(value["domain"]), str(value["name"]))):
        fields = [str(cookie.get(key) or "") for key in ("domain", "path", "name", "value")]
        if any("\t" in value or "\n" in value or "\r" in value for value in fields):
            raise CookieRefreshError("Cookie 包含非法控制字符")
        domain, path, name, value = fields
        include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
        secure = "TRUE" if cookie.get("secure") else "FALSE"
        # Netscape cookie.txt 用 0 表示会话 Cookie；负数会让 yt-dlp 把整行
        # （包含 Cookie 值）写入 warning，因此必须在落盘前规范化。
        expires = max(0, int(float(cookie.get("expires") or 0)))
        if cookie.get("httpOnly"):
            domain = "#HttpOnly_" + domain
        lines.append("\t".join((domain, include_subdomains, path or "/", secure, str(expires), name, value)))
    return "\n".join(lines) + "\n"


def wait_for_required_cookies(context, page, timeout_ms: int = 5_000) -> list[dict]:
    """详情接口返回后，等待异步 Set-Cookie 完成，避免写入不完整的 jar。"""
    deadline = time.monotonic() + max(0, timeout_ms) / 1000
    cookies = context.cookies()
    while not REQUIRED_COOKIES.issubset({str(cookie.get("name") or "") for cookie in cookies}):
        if time.monotonic() >= deadline:
            return cookies
        page.wait_for_timeout(250)
        cookies = context.cookies()
    return cookies


def write_cookie_jar(output: Path, text: str) -> None:
    """Atomically replace the jar; a failed refresh leaves the old jar intact."""
    if output.is_symlink():
        raise CookieRefreshError("拒绝覆盖符号链接形式的 Cookie 文件")
    if output.parent.is_symlink():
        raise CookieRefreshError("拒绝写入符号链接形式的 Cookie 目录")
    if not output.parent.exists():
        output.parent.mkdir(parents=True, mode=0o700)
    directory_mode = stat.S_IMODE(output.parent.stat().st_mode)
    if directory_mode & 0o077:
        raise CookieRefreshError("Cookie 目录权限过宽，请先设置为 0700")
    fd, temp_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent, text=True)
    temp_path = Path(temp_name)
    try:
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, output)
        output.chmod(0o600)
    finally:
        temp_path.unlink(missing_ok=True)


def refresh(
    output: Path,
    seed_url: str,
    timeout_ms: int = 60_000,
    executable_path: str | None = None,
) -> int:
    browser_path: Path | None = None
    if executable_path:
        browser_path = Path(executable_path).expanduser()
        if not browser_path.is_file():
            raise CookieRefreshError("配置的 Chromium 可执行文件不存在")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise CookieRefreshError("缺少 Playwright：先安装项目的 browser 可选依赖") from exc

    with sync_playwright() as playwright:
        launch_options: dict = {"headless": True, "args": ["--disable-dev-shm-usage"]}
        if browser_path:
            launch_options["executable_path"] = str(browser_path)
        browser = playwright.chromium.launch(**launch_options)
        try:
            context = browser.new_context(locale="zh-CN")
            page = context.new_page()
            with page.expect_response(
                lambda response: "/aweme/v1/web/aweme/detail/" in response.url and response.status == 200,
                timeout=timeout_ms,
            ) as response_info:
                page.goto(seed_url, wait_until="domcontentloaded", timeout=timeout_ms)
            payload = response_info.value.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("aweme_detail"), dict):
                raise CookieRefreshError("抖音详情接口没有返回作品数据，匿名会话可能被风控")
            cookies = wait_for_required_cookies(context, page, min(timeout_ms, 10_000))
        finally:
            browser.close()

    text = netscape_cookie_text(cookies)
    write_cookie_jar(output, text)
    return sum(1 for cookie in cookies if _is_douyin_cookie(cookie))


def main() -> None:
    parser = argparse.ArgumentParser(description="安全刷新匿名抖音 Cookie 文件")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(os.getenv("DOUYIN_COOKIES_FILE", "~/douyin-cookies.txt")).expanduser(),
    )
    parser.add_argument("--seed-url", default=os.getenv("DOUYIN_COOKIE_SEED_URL", DEFAULT_SEED_URL))
    parser.add_argument(
        "--browser-executable",
        default=os.getenv("DOUYIN_CHROMIUM_EXECUTABLE") or None,
        help="可选：显式指定服务器上的 Chromium/Chrome 可执行文件",
    )
    parser.add_argument("--timeout-ms", type=int, default=60_000)
    args = parser.parse_args()
    count = refresh(args.output, args.seed_url, args.timeout_ms, args.browser_executable)
    print(f"匿名 Cookie 已安全刷新：{count} 项，文件权限 0600")


if __name__ == "__main__":
    main()
