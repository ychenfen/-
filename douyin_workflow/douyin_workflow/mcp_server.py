"""MCP 服务：在 Claude Code / Claude Desktop 里粘贴抖音口令即可拿到逐字稿。

    claude mcp add douyin -- python -m douyin_workflow.mcp_server
"""

from __future__ import annotations

import logging
import sys

try:  # mcp >= 2.0
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from . import pipeline

# stdio 模式下 stdout 专供 JSON-RPC，日志一律走 stderr
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

mcp = _Server("douyin")


@mcp.tool()
def douyin_to_text(share_text: str, force: bool = False) -> dict:
    """把抖音分享口令（或链接）转成逐字稿。

    直接粘贴从抖音 App 复制的整段口令即可，例如
    "7.43 复制打开抖音，看看【某某的作品】… https://v.douyin.com/xxxx/ ..."。
    返回 title、author、duration_s、transcript，以及用了哪个下载后端。
    同一作品第二次请求直接读本地缓存；force=True 强制重新下载和转写。
    首次调用要加载转写模型，可能需要几十秒。
    """
    return pipeline.run_safe(share_text, force=force)


@mcp.tool()
def douyin_list_local(limit: int = 20) -> list[dict]:
    """列出本地素材库里最近处理过的作品（标题、作者、时长、目录），不含逐字稿正文。"""
    return pipeline.list_local(limit)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
