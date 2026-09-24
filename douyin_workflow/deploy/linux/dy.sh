#!/usr/bin/env bash
# 用法：~/dy2text/dy.sh "抖音分享口令或链接"
# 调本机 dy2text 服务，循环等待直到出结果，打印逐字稿。
set -euo pipefail
TOKEN=$(grep ^DOUYIN_SERVER_TOKEN= ~/dy2text/dy2text.env | cut -d= -f2-)
BODY=$(python3 -c "import json,sys;print(json.dumps({\"text\":sys.argv[1]}))" "$1")
for i in $(seq 1 60); do
  R=$(curl -s -m 40 -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "$BODY" http://127.0.0.1:8765/transcribe)
  S=$(printf %s "$R" | python3 -c "import json,sys;print(json.load(sys.stdin)[\"status\"])")
  if [ "$S" != running ]; then printf %s "$R" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d[\"text\"]);sys.exit(0 if d[\"status\"]==\"done\" else 1)"; exit $?; fi
  echo "…$(printf %s "$R" | python3 -c "import json,sys;print(json.load(sys.stdin)[\"text\"])")" >&2
done
echo "超时" >&2; exit 1
