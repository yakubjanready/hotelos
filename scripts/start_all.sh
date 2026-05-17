#!/usr/bin/env bash
# HotelOS — barcha mikroservislarni fonda ishga tushirish.
#
# Ushbu skript Redis ishlab turganini tekshiradi, keyin 4 ta mikroservis va
# panel servisini alohida loglar bilan ishga tushiradi. Har bir servisning PID
# raqami logs/ papkasiga yoziladi, shunda stop_all.sh ularni to'xtata oladi.

set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p logs

echo "🔧 Redis ulanishini tekshirish..."
if command -v redis-cli >/dev/null 2>&1; then
  redis-cli ping >/dev/null 2>&1 || {
    echo "⚠️  Redis ishlamayapti — 'docker compose up -d' bilan ishga tushiring."
    exit 1
  }
  echo "   Redis OK"
else
  echo "⚠️  redis-cli yo'q — Redis ulanishini qo'lda tekshiring."
fi

start_service() {
  local name="$1"
  local module="$2"
  echo "🚀 $name ishga tushmoqda..."
  nohup python3 -m "$module" > "logs/${name}.log" 2>&1 &
  echo $! > "logs/${name}.pid"
  sleep 0.5
}

start_service reception     reception_service.main
start_service housekeeping  housekeeping_service.main
start_service roomservice   roomservice_service.main
start_service maintenance   maintenance_service.main
start_service dashboard     dashboard_service.main

echo ""
echo "✅ Barcha servislar ishga tushdi."
echo "   Panel:        http://localhost:8000"
echo "   Reception:    http://localhost:8001/docs"
echo "   Housekeeping: http://localhost:8002/docs"
echo "   Room Service: http://localhost:8003/docs"
echo "   Maintenance:  http://localhost:8004/docs"
echo ""
echo "   Loglar:       logs/<servis>.log"
echo "   To'xtatish:   scripts/stop_all.sh"
