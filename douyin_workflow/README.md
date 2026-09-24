# 抖音对标素材工作流 · 第 1 步 MVP

把抖音分享口令粘贴给 Claude，就能在本地完成下载、转写，并返回逐字稿、标题、作者和时长。Claude 拿到后可以接着做拆解和改写。

```
分享口令 → 提取链接/短链跳转 → 作品 ID
        → 下载：iesdouyin 分享页 → f2 → yt-dlp（前一个失败自动换下一个）
        → ffmpeg 抽 16k 音频 → FunASR 转写（paraformer-zh / SenseVoiceSmall）
        → 落盘 <DOUYIN_DATA_DIR>/<作品ID>/ { meta.json, transcript.txt, audio.wav }
```

> 必须在**你自己的电脑**上运行。Claude 的云端环境访问不了抖音。

## 安装

需要 Python ≥ 3.10 和 ffmpeg（Windows：`winget install ffmpeg`；Ubuntu：`sudo apt install ffmpeg`；Mac：`brew install ffmpeg python@3.12`）。

> **Mac 用户**：系统自带的 `python3` 可能是 3.9，请用 Homebrew 装的 `python3.12` 建 venv（`python3.12 -m venv .venv`）。Mac 没有 CUDA，转写默认走 CPU，不需要单独装 GPU 版 torch，直接执行下面的 `pip install -e ".[asr]"` 即可。

```bash
cd douyin_workflow
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate

# 有 NVIDIA 显卡：先按 https://pytorch.org 装对应 CUDA 版本的 torch/torchaudio
# 例如：pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -e ".[asr]"

# 可选：f2 后端
pip install f2 && pip install -U "pydantic>=2.11"
```

> f2 把 pydantic 锁在 2.9，而 mcp 需要更新的版本，所以装完 f2 要再升级一次 pydantic。实测 f2 在新版 pydantic 下能正常导入。不想处理这个问题可以不装 f2，下载链会跳过它。

先用命令行试一下。第一次运行会从 modelscope 下载约 1GB 模型：

```bash
python -m douyin_workflow run "7.43 复制打开抖音，看看【xx的作品】... https://v.douyin.com/xxxx/ ..."
python -m douyin_workflow list
```

## 接到 Claude

**Claude Code**（在 `douyin_workflow` 目录、已激活 venv 的终端里执行）：

```bash
claude mcp add douyin -e DOUYIN_DATA_DIR=D:/douyin_data -- python -m douyin_workflow.mcp_server
```

**Claude Desktop**，编辑 `claude_desktop_config.json`（Mac 在 `~/Library/Application Support/Claude/`，Windows 在 `%APPDATA%\Claude\`），`command` 填 venv 里 python 的绝对路径（Mac 形如 `/Users/<你>/douyin_workflow/.venv/bin/python`）：

```json
{
  "mcpServers": {
    "douyin": {
      "command": "D:/code/douyin_workflow/.venv/Scripts/python.exe",
      "args": ["-m", "douyin_workflow.mcp_server"],
      "env": { "DOUYIN_DATA_DIR": "D:/douyin_data" }
    }
  }
}
```

配置好后提供两个工具：

| 工具 | 作用 |
|---|---|
| `douyin_to_text(share_text, force=False)` | 口令 → 逐字稿和元数据。同一作品会读缓存，`force=True` 强制重跑 |
| `douyin_list_local(limit=20)` | 列出本地素材库最近处理的作品 |

失败时返回 `{"error": ..., "message": ...}`，不会抛异常。下载失败还会附上每个后端各自的失败原因。

用法示例：*"把这条转成文字，拆一下开头 3 秒的钩子、论证结构和用到的数据，再按我的口吻改写成 60 秒口播：<粘贴口令>"*

## 配置（环境变量）

| 变量 | 默认 | 说明 |
|---|---|---|
| `DOUYIN_DATA_DIR` | `~/douyin_workflow_data` | 素材库目录 |
| `DOUYIN_BACKENDS` | `iesdouyin,f2,ytdlp` | 下载后端顺序 |
| `DOUYIN_COOKIE` | – | 网页版 douyin.com 的 cookie 字符串（f2 用），从浏览器开发者工具复制 |
| `DOUYIN_COOKIES_FILE` | – | Netscape 格式 cookies.txt（yt-dlp 用） |
| `DOUYIN_COOKIES_FROM_BROWSER` | – | 让 yt-dlp 直接读浏览器 cookie，如 `chrome`、`edge`、`firefox` |
| `DOUYIN_MIN_INTERVAL` | `8` | 两次下载请求的最小间隔（秒） |
| `DOUYIN_ASR_MODEL` | `paraformer-zh` | 也可以用 `SenseVoiceSmall`，速度更快，对口语和方言更友好 |
| `DOUYIN_ASR_DEVICE` | `auto` | `auto` 表示有 CUDA 就用 GPU，也可指定 `cuda:0` 或 `cpu` |
| `DOUYIN_KEEP_VIDEO` | `0` | 设为 `1` 时保留 mp4，默认转写完就删 |
| `DOUYIN_HEALTH_URLS` | – | 健康检查用的固定作品链接，逗号分隔 |
| `DOUYIN_ALERT_WEBHOOK` | – | 健康检查失败时 POST `{"title","body"}` 到这个地址，例如 Bark 的 `https://api.day.app/<key>` |

## 稳定性：坏了能很快发现、很快切换

- **自动降级**：每次结果的 `meta.json` 里都有 `backend`（实际用的后端）和 `fallback_errors`（前面哪些后端失败了、为什么）。如果首选后端一直出现在 `fallback_errors` 里，说明它已经坏了，即使最终下载成功也要注意。
- **健康检查**：逐个后端单独下载固定链接，只下载不转写。

  ```bash
  python -m douyin_workflow healthcheck   # 退出码 0 全部正常 / 1 部分后端坏了 / 2 全部失败
  ```

  Linux 或 Mac 用 cron 每天跑一次（`crontab -e`）：`0 9 * * * cd /path/douyin_workflow && .venv/bin/python -m douyin_workflow healthcheck`
  Windows 用"任务计划程序"，程序填 `.venv\Scripts\python.exe`，参数填 `-m douyin_workflow healthcheck`。
- **限速**：进程内两次请求至少间隔 `DOUYIN_MIN_INTERVAL` 秒。一天几十条问题不大，批量上百条容易触发风控。
- **缓存**：处理过的作品不会再次访问抖音。

常见故障：

| 现象 | 处理 |
|---|---|
| iesdouyin 报"没找到 _ROUTER_DATA" | 分享页改版了，先靠后面的后端兜底，再更新 `downloaders/iesdouyin.py` 的解析 |
| yt-dlp 报 "Fresh cookies are needed" | 配置 `DOUYIN_COOKIES_FROM_BROWSER=chrome`，或导出 cookies.txt。Mac 上第一次读 Chrome cookie 会弹钥匙串授权，点“允许”；用 Safari 需要给终端开“完全磁盘访问权限”，建议直接用 Chrome |
| f2 报 a_bogus / msToken 相关错误 | `pip install -U f2`，并更新 `DOUYIN_COOKIE` |
| 下载到的文件"过小" | 多半被风控，降低频率或换网络 |

## 边界

只作为**自用的对标素材库**，保存逐字稿和拆解结果。不做公开网站，不展示或转载他人的视频和文案。

## 测试

```bash
pip install -e ".[dev]" && pytest
```

测试全部离线运行，网络请求和 FunASR 都用替身代替。

## 后续步骤

1. ✅ MVP：本地下载降级 + FunASR + MCP 工具
2. 入库（Postgres + 向量索引）+ LLM 结构化拆解（钩子、结构、论点、数据、违禁词）
3. 网页后台：检索、爆款对比、一键改写口语稿
4. 接入卡片和剪映产线，健康检查告警接入统一通知
