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

## iPhone 快捷指令：复制链接，点一下就出文字

```
iPhone：复制抖音/微信里的链接 → 轻点手机背面两下（或点桌面图标）
   ↓  快捷指令把链接发给家里的 Mac
Mac：下载 → 转写（视频转完即删）
   ↓
iPhone：弹出逐字稿，同时已经复制到剪贴板，可以直接粘贴给老板
```

### 1. Mac 端：装成开机自启服务

先按上面的「安装」装好，并在终端里跑通一次 `python -m douyin_workflow run "<口令>"`。第一次读取 Chrome cookie 时，Mac 会弹出"钥匙串"窗口，请点"始终允许"。然后执行：

```bash
bash deploy/macos/install.sh
```

脚本会注册一个登录后自动启动的后台服务（端口 8765），生成一个 token，并打印快捷指令要填的**地址**和 **Authorization**，请记下来。重复执行也不会丢失 token，停用方法见脚本输出。

另外要防止 Mac 睡眠：打开"系统设置 → 电池（或能源）→ 选项"，勾选"接电源时防止自动进入睡眠"。

**在外面也想用**：Mac 和 iPhone 都安装 [Tailscale](https://tailscale.com)，并登录同一个账号，重新执行一次 `install.sh`，它会额外打印一个 `100.x.x.x` 的地址。只在家里用的话，同一个 Wi-Fi 下用 `http://你的Mac名.local:8765` 就行。

### 2. iPhone 端：搭快捷指令（大约 5 分钟）

打开「快捷指令」App → 右上角 **+** → 名字改成 **抖音转文字**，依次添加下面的动作：

1. **获取剪贴板**
2. **重复** 20 次，在重复块里面依次添加：
   1. **获取 URL 内容**
      - URL：填 install.sh 打印的地址，例如 `http://xxx.local:8765/transcribe`
      - 展开"显示更多" → 方法选 **POST**
      - 头部：添加一项，键填 `Authorization`，值填 `Bearer 你的token`（Bearer 后面有一个空格）
      - 请求体选 **JSON**，添加一个"文本"字段，键填 `text`，值选变量 **剪贴板**
   2. **获取词典值**：获取 `status` 的值，词典选上一步的"URL 的内容"
   3. **如果** "词典值" **不是** `running`：
      - **获取词典值**：获取 `text` 的值，词典选"URL 的内容"
      - **拷贝到剪贴板**：词典值
      - **快速查看**：词典值
      - **停止此快捷指令**
   4. **结束如果**
3. 在"结束重复"后面添加 **显示通知**：`还在处理，过一两分钟再点一次，做完会立刻返回`

每次请求最多等 25 秒，20 次循环最多等 8 分钟左右。一条 1～3 分钟的视频通常一两轮就能返回。同一条链接再点一次会直接从缓存返回。

**触发方式**（选一个就行）：
- **轻点背面**：打开"设置 → 辅助功能 → 触控 → 轻点背面 → 轻点两下"，选择「抖音转文字」。复制链接后敲两下手机背面就开始转写。
- 把快捷指令添加到主屏幕，或者对 Siri 说"抖音转文字"。

链接来源：在抖音里点"分享 → 复制链接"；老板在微信发来的口令或链接，长按后选"复制"即可。

### 常见问题

| 现象 | 处理 |
|---|---|
| 快捷指令报"无法连接到服务器" | Mac 睡眠了或关机了；或者手机不在同一个 Wi-Fi 上，又没有开 Tailscale |
| 返回"token 不对" | 检查 Authorization 的值，应该是 `Bearer ` 加 token，中间有一个空格 |
| 返回"处理失败：所有下载后端都失败了" | 多半是 cookie 过期：在 Mac 的 Chrome 里重新打开 douyin.com，然后再试 |
| 其他问题 | 查看 Mac 上的日志 `~/Library/Logs/douyin-workflow/server.log` |

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
| `DOUYIN_SERVER_TOKEN` | – | `serve` 服务的访问口令（install.sh 自动生成） |
| `DOUYIN_SERVER_PORT` | `8765` | `serve` 服务端口 |
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

1. ✅ MVP：本地下载降级 + FunASR + MCP 工具 + iPhone 快捷指令
2. 入库（Postgres + 向量索引）+ LLM 结构化拆解（钩子、结构、论点、数据、违禁词）
3. 网页后台：检索、爆款对比、一键改写口语稿
4. 接入卡片和剪映产线，健康检查告警接入统一通知

## 部署到云服务器（手机浏览器直接用）

小内存服务器（实测 4 核 / 3.3 GB，可用约 1.3 GB）装不下 FunASR + torch，改用 sherpa-onnx 跑 SenseVoice int8 模型：约 230 MB，纯 CPU，不需要 API 密钥。一段 15 秒中文语音转写约 2 秒，进程内存峰值约 410 MB。长音频按 25 秒左右切段，切点取前后 5 秒内最安静的位置，避免把词切断。

服务启动后访问根路径 `/` 是一个手机素材台：粘贴抖音口令后，页面会轮询 `/transcribe` 直到出结果。逐字稿可以直接校对，也可以复制纯文本或完整信息、下载 TXT、生成一段用于事实核查和深入研究的提示词；浏览器只保留最近 5 条标题和作品 ID。访问密码就是 `DOUYIN_SERVER_TOKEN`，只存在当前浏览器的 `localStorage`。页面全部使用相对路径，可以挂在 nginx 的任意前缀下。

```bash
# 1. 代码与依赖（在 ~/dy2text 下）
python3 -m venv venv
venv/bin/pip install requests yt-dlp sherpa-onnx numpy imageio-ffmpeg
ln -sf "$(venv/bin/python -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')" venv/bin/ffmpeg
rsync -a douyin_workflow/ ~/dy2text/app/        # 本仓库的 douyin_workflow 目录

# 2. 模型（国内用 hf-mirror，GitHub release 很慢）
mkdir -p models/sensevoice && cd models/sensevoice
B=https://hf-mirror.com/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main
curl -LO $B/model.int8.onnx && curl -LO $B/tokens.txt && cd ../..

# 3. 配置、服务、反代
cp app/deploy/linux/dy2text.env.example dy2text.env && chmod 600 dy2text.env   # 填 TOKEN
sudo cp app/deploy/linux/dy2text.service /etc/systemd/system/ && sudo systemctl enable --now dy2text
# 把 deploy/linux/nginx-location.conf 放进已有 HTTPS 站点的 server 块，nginx -t 后 reload
```

在服务器上命令行处理一条链接（和网页共用缓存）：`~/dy2text/dy.sh "<分享口令>"`，脚本见 `deploy/linux/dy.sh`。

注意：机房 IP 比家用宽带更容易被抖音风控。无 cookie 的 `iesdouyin` 后端失败时，给 `ytdlp` 配 `DOUYIN_COOKIES_FILE` 再试。
