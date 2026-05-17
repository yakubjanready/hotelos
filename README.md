# HotelOS — Real Vaqtli Mehmonxona Boshqaruv Tizimi

BTEC Pearson 4-Modul "Dasturlash" (H/618/7388) topshirig'i.

HotelOS — 120 xonali mehmonxonani boshqaruvchi real vaqtli tizim. To'rtta
mustaqil mikroservis Redis Pub/Sub broker orqali muloqot qiladi va WebSocket
asosida brauzer/terminal panellariga jonli yangilanish uzatadi.

---

## Tezkor boshlash (Quick Start)

### Talablar

- Python 3.11+ (3.10 ham ishlaydi)
- Docker (Redis uchun) yoki lokal Redis o'rnatish
- pip yoki uv paket boshqaruvchisi

### O'rnatish

```bash
# 1. Loyihaga kiring
cd hotelos

# 2. Virtual muhit yarating (tavsiya etiladi)
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Bog'liqliklarni o'rnating
pip install -r requirements.txt

# 4. .env faylini yarating (bo'sh qoldirsa sukut qiymatlari ishlatiladi)
cp .env.example .env

# 5. Redis brokerini Docker bilan ishga tushiring
docker compose up -d
```

### Ishga tushirish (bir buyruq)

```bash
./scripts/start_all.sh
```

Bu skript Redis ulanishini tekshiradi va 5 ta servisni alohida fonda
ishga tushiradi:

| Servis | URL | Tavsif |
|--------|-----|--------|
| Panel | http://localhost:8000 | Operatsion brauzer paneli |
| Reception | http://localhost:8001/docs | Check-in/check-out + Swagger |
| Housekeeping | http://localhost:8002/docs | Tozalash navbati |
| Room Service | http://localhost:8003/docs | Buyurtmalar |
| Maintenance | http://localhost:8004/docs | Texnik xizmat |

Loglar `logs/` papkasiga yoziladi.

### Panelga kirish

1. Brauzerda http://localhost:8000 ni oching
2. Login: `admin` / parol: `admin123` (sukut qiymatlari — `.env` da o'zgartirish mumkin)
3. Real vaqtli xona setkasi, faol buyurtmalar va texnik muammolar ko'rinadi

### Terminal monitor

```bash
python3 -m terminal_monitor.monitor --login admin:admin123
```

### To'xtatish

```bash
./scripts/stop_all.sh
docker compose down
```

---

## Test stsenariylarini ishga tushirish

```bash
# 1. Servislar ishlab turganini tekshiring
curl http://localhost:8001/health

# 2. Avtomatlashtirilgan 8 ta stsenariyni ishga tushiring
python3 scripts/run_test_scenarios.py

# Natija: docs/test_results.md
```

Birlik testlari (pytest):

```bash
pytest -v                          # barchasi
pytest tests/test_algorithms.py -v # faqat algoritm testlari
```

Algoritm demosi (Redis kerak emas):

```bash
python3 scripts/demo_algorithms.py
```

---

## Arxitektura

```
                       ┌──────────────┐
       ┌──────────────►│   Redis      │◄──────────────┐
       │               │   Pub/Sub    │               │
       │               └──────┬───────┘               │
       │                      │ (subscribe all)       │
       │                      ▼                       │
┌──────┴──────┐         ┌──────────┐         ┌────────┴────────┐
│  Reception  │         │Dashboard │         │  Housekeeping   │
│  :8001      │◄────────┤  :8000   │         │  :8002          │
│             │  HTTP   │ WebSocket│         │                 │
└──────┬──────┘         └────┬─────┘         └─────────────────┘
       │                     │
       │  HTTP /internal     │ WS
       │                     ▼
┌──────┴──────┐         ┌──────────┐
│ Room Service│         │ Brauzer/ │
│  :8003      │         │ Terminal │
└─────────────┘         └──────────┘
       │
       ▼
┌─────────────┐
│ Maintenance │
│  :8004      │
└─────────────┘
```

**Asosiy texnologiyalar:** Python 3.11 · FastAPI · Redis Pub/Sub · WebSocket ·
Pydantic v2 · pytest · rich (TUI) · Tailwind CSS (brauzer paneli).

To'liq arxitektura tavsifi: `docs/diagram_architecture.png` va hisobotning 3.1
bo'limi.

---

## Asosiy algoritmlar

| Algoritm | Fayl | Blok-sxema |
|----------|------|------------|
| Xona tayinlash (5 mezonli) | `reception_service/algorithms.py:assign_room` | `docs/diagram_room_assignment.png` |
| Hisob-kitob | `reception_service/algorithms.py:calculate_bill` | `docs/diagram_billing.png` |
| Texnik ustuvorlik navbati | `maintenance_service/priority_queue.py` | `docs/diagram_priority_queue.png` |

---

## Loyiha tuzilmasi

```
hotelos/
├── shared/                    # Umumiy modullar (config, models, broker, security)
├── reception_service/         # Check-in/check-out + algoritmlar
├── housekeeping_service/      # Tozalash navbati
├── roomservice_service/       # Ovqat buyurtmalari
├── maintenance_service/       # Texnik xizmat + priority queue
├── dashboard_service/         # WebSocket panel
├── terminal_monitor/          # rich TUI
├── tests/                     # pytest birlik testlari
├── scripts/                   # ishga tushirish va demo skriptlari
├── data/                      # rooms.json (120 xona), menu.json
└── docs/                      # blok-sxemalar va hisobot
```

---

## Xavfsizlik mulohazalari

- **Kiritishni tekshirish** — `shared/security.py:InputValidator` har bir tashqi
  ma'lumotni qayta ishlashdan oldin tekshiradi.
- **Autentifikatsiya** — JWT (HMAC-SHA256) token bilan dashboard himoyalangan.
- **Ma'lumotlarni oshkor qilish nazorati** — `redact_sensitive()` panel
  uzatmalarini filtrlaydi.
- **Xatolarni boshqarish** — hech qaerda xom stek izi foydalanuvchiga ko'rinmaydi.

---

## Git tarixi

```
git log --oneline --graph --all
```

Loyihada 17+ mazmunli git majburiyati, har biri bir mantiqiy o'zgarish.

---

## Litsenziya

Akademik topshiriq. To'liq mualliflik talaba (Yoqubjon, BTEC 4-Modul) ga
tegishli.

---

## Tegishli fayllar

- **Hisobot:** `docs/Yoqubjon_HotelOS_Hisobot.docx`
- **Demo chiqishi:** `docs/demo_output.txt`
- **Test natijalar:** `docs/test_results.md` (run_test_scenarios.py ishga
  tushganidan keyin)

---

*Yoqubjon · BTEC Pearson 4-Modul: Dasturlash · 2026 May*
