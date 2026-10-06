#!/bin/sh
set -eu
cd "$(dirname "$0")"
node scripts/preview.mjs stop >/dev/null 2>&1 || true
if curl -sf -o /dev/null --max-time 2 http://127.0.0.1:8080/; then
  echo "Range Bench is already running at http://127.0.0.1:8080"
  exit 0
fi
if [ ! -d node_modules ]; then
  echo "Dependencies are not installed. Run: sh scripts/install.sh"
  exit 1
fi
npm run dev >>/tmp/app-startup.log 2>&1 &
i=0
while [ "$i" -lt 40 ]; do
  if curl -sf -o /dev/null --max-time 1 http://127.0.0.1:8080/; then
    echo "Range Bench is running at http://127.0.0.1:8080"
    exit 0
  fi
  i=$((i + 1))
  sleep 0.5
done
echo "The page did not answer on port 8080. The log is /tmp/app-startup.log"
tail -n 30 /tmp/app-startup.log 2>/dev/null || true
exit 1
