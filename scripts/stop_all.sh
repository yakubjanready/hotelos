#!/usr/bin/env bash
# HotelOS servislarini xavfsiz to'xtatish.

set -euo pipefail
cd "$(dirname "$0")/.."

for pidfile in logs/*.pid; do
  [ -f "$pidfile" ] || continue
  name=$(basename "$pidfile" .pid)
  pid=$(cat "$pidfile")
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" && echo "🛑 $name to'xtatildi (PID $pid)"
  else
    echo "ℹ️  $name allaqachon to'xtagan"
  fi
  rm -f "$pidfile"
done
