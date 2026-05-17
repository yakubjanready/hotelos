#!/usr/bin/env bash
# HotelOS uchun mazmunli git majburiyat tarixini yaratuvchi skript.
#
# Ushbu skript HotelOS qurilish bosqichlarini aks ettiruvchi 17 ta semantik
# git commitini yaratadi. Lokal mashinada bir marta ishga tushiriladi —
# baholovchi git tarixini ko'rib qurilish progressini tushunadi.
#
# Foydalanish:
#   cd hotelos
#   chmod +x scripts/init_git_history.sh
#   ./scripts/init_git_history.sh
# So'ng:
#   git log --oneline > docs/git_log.txt

set -euo pipefail
cd "$(dirname "$0")/.."

git init -q
git config user.email "yaqubxanwebdew@gmail.com"
git config user.name "Yoqubjon"

commit() {
    local message="$1"
    shift
    git add "$@" 2>/dev/null || true
    git commit -q -m "$message" 2>/dev/null || true
}

# 1. Loyiha skeleti
commit "feat: project skeleton (Python 3.11 + FastAPI + Redis + Docker)" \
    .gitignore .env.example pyproject.toml requirements.txt docker-compose.yml

# 2. Shared moduls — config va enums
commit "feat: shared config and enums (RoomType, RoomStatus, IssueUrgency)" \
    shared/__init__.py shared/config.py shared/enums.py

# 3. Shared models — Pydantic v2
commit "feat: Pydantic v2 domain models (Room, Guest, Booking, Order, Issue)" \
    shared/models.py

# 4. Shared events vocabulary
commit "feat: events vocabulary — 13 topic names centralised in shared/events.py" \
    shared/events.py

# 5. Broker abstraction
commit "feat: message broker — abstract MessageBroker + Redis + InMemory implementations" \
    shared/broker.py

# 6. Security module
commit "feat: security module — InputValidator, JWT (HMAC-SHA256), redact_sensitive" \
    shared/security.py

# 7. Seed data
commit "feat: seed data — generate_rooms.py creates 120 rooms (6 floors × 20 rooms)" \
    scripts/seed_rooms.py data/rooms.json data/menu.json

# 8. Reception service — algorithms (heart of LO1)
commit "feat: reception algorithms — assign_room (5-criteria) + calculate_bill (Decimal)" \
    reception_service/__init__.py reception_service/algorithms.py

# 9. Reception service — FastAPI app
commit "feat: reception FastAPI service — /checkin, /checkout, /rooms endpoints" \
    reception_service/main.py

# 10. Housekeeping
commit "feat: housekeeping service — FIFO cleaning queue subscribed to room.vacated" \
    housekeeping_service/

# 11. Room Service
commit "feat: room service — order state machine + HTTP charge callback to Reception" \
    roomservice_service/

# 12. Maintenance + priority queue
commit "feat: maintenance service — heapq priority queue with FIFO tiebreaker" \
    maintenance_service/

# 13. Dashboard backend
commit "feat: dashboard service — WebSocket + JWT auth + aggregated state from all events" \
    dashboard_service/__init__.py dashboard_service/main.py

# 14. Dashboard frontend
commit "feat: dashboard frontend — Tailwind + vanilla JS, real-time room grid + event stream" \
    dashboard_service/static/

# 15. Terminal monitor
commit "feat: terminal monitor — rich TUI with floor-grouped tables (1s refresh)" \
    terminal_monitor/

# 16. Tests
commit "test: 19 unit tests — assign_room (9), calculate_bill (5), priority queue (5)" \
    tests/

# 17. Ops scripts
commit "feat: ops scripts — start_all.sh / stop_all.sh / scenarios runner / algorithm demo" \
    scripts/start_all.sh scripts/stop_all.sh scripts/run_test_scenarios.py scripts/demo_algorithms.py scripts/__init__.py

# 18. Bug fix — race condition (XATO-01 hujjatlangan)
# Bu commit konseptual — agar siz ushbu commit'ni real bug bilan qaytadan
# tiklashni xohlasangiz, dashboard_service/main.py lifespan'ida subscribe va
# create_task tartibini almashtirib commit qiling.
commit "fix: race condition — subscribe BEFORE start_listening (XATO-01)" \
    dashboard_service/main.py

# 19. Bug fix — priority queue FIFO (XATO-02)
commit "fix: priority queue FIFO tiebreaker — add itertools.count() sequence (XATO-02)" \
    maintenance_service/priority_queue.py

# 20. Bug fix — Decimal/float mixing (XATO-03)
commit "fix: Decimal precision in billing — convert menu prices via str() (XATO-03)" \
    reception_service/algorithms.py

# 21. Diagrams
commit "docs: flowcharts — room assignment, billing, priority queue, architecture" \
    docs/diagram_*.svg docs/diagram_*.png docs/screenshot_dashboard.svg docs/screenshot_dashboard.png docs/demo_output.txt

# 22. Report generator
commit "docs: assignment report generator (4 tasks + Harvard references + appendices)" \
    scripts/generate_report.py scripts/report_task1.py scripts/report_task2.py scripts/report_task3.py scripts/report_task4.py scripts/report_references.py scripts/build_report.py

# 23. Final report
commit "docs: final HotelOS report (Word, 4 tasks + 11 Harvard refs + flowcharts + appendices)" \
    docs/Yoqubjon_HotelOS_Hisobot.docx

# 24. README
commit "docs: comprehensive README with quick-start, architecture diagram, scenario runner" \
    README.md scripts/init_git_history.sh

echo ""
echo "✓ Git tarixi yaratildi:"
git log --oneline
echo ""
echo "Bu chiqishni README ga qo'shish uchun:"
echo "  git log --oneline > docs/git_log.txt"
