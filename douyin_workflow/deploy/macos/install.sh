#!/bin/bash
# 把转写服务注册成 macOS 登录自启的后台服务（LaunchAgent）。
# 在 douyin_workflow 目录下、装好 .venv 之后运行：  bash deploy/macos/install.sh
# 重复运行是安全的：会保留已有 token，只刷新配置并重启服务。
set -euo pipefail

LABEL="com.douyin-workflow.server"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$ROOT/.venv/bin/python"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
ENV_FILE="$HOME/.douyin_workflow.env"
LOG_DIR="$HOME/Library/Logs/douyin-workflow"
PORT="${DOUYIN_SERVER_PORT:-8765}"

if [ ! -x "$PY" ]; then
  echo "找不到 $PY，请先在 $ROOT 下建 .venv 并 pip install -e '.[asr]'" >&2
  exit 1
fi
command -v ffmpeg >/dev/null || { echo "找不到 ffmpeg，请先 brew install ffmpeg" >&2; exit 1; }

# token 只生成一次，存在 ~/.douyin_workflow.env
if [ ! -f "$ENV_FILE" ]; then
  echo "DOUYIN_SERVER_TOKEN=$(openssl rand -hex 16)" > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
fi
TOKEN="$(grep '^DOUYIN_SERVER_TOKEN=' "$ENV_FILE" | cut -d= -f2)"

mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"

# launchd 的 PATH 很短，要把 Homebrew 的 ffmpeg 目录加进去
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string><string>-m</string><string>douyin_workflow</string>
    <string>serve</string><string>--port</string><string>$PORT</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>DOUYIN_SERVER_TOKEN</key><string>$TOKEN</string>
    <key>DOUYIN_COOKIES_FROM_BROWSER</key><string>${DOUYIN_COOKIES_FROM_BROWSER:-chrome}</string>
    <key>DOUYIN_DATA_DIR</key><string>${DOUYIN_DATA_DIR:-$HOME/douyin_workflow_data}</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$LOG_DIR/server.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/server.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

HOST="$(scutil --get LocalHostName 2>/dev/null || hostname -s).local"
TS_IP="$(command -v tailscale >/dev/null && tailscale ip -4 2>/dev/null | head -1 || true)"

cat <<EOF

✅ 服务已启动并设为登录自启。日志：$LOG_DIR/server.log

在快捷指令里填：
  地址（同一 Wi-Fi）：http://$HOST:$PORT/transcribe
EOF
[ -n "$TS_IP" ] && echo "  地址（在外面，Tailscale）：http://$TS_IP:$PORT/transcribe"
cat <<EOF
  Authorization：Bearer $TOKEN

自测：curl -s -X POST http://localhost:$PORT/transcribe -H "Authorization: Bearer $TOKEN" -d '<粘贴抖音口令>'
停用：launchctl bootout gui/\$(id -u)/$LABEL
EOF
