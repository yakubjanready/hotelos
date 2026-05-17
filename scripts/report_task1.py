"""1-Vazifa kontenti — algoritmlar va kod jarayoni."""

from pathlib import Path

from scripts.generate_report import (
    DOCS,
    add_code,
    add_heading,
    add_image,
    add_para,
    add_table,
    add_table_caption,
    page_break,
)


def task1(doc):
    page_break(doc)
    add_heading(doc, "1-Vazifa — Algoritmlar va Kod Jarayoni (LO1)", level=1)
    add_para(
        doc,
        "Ushbu vazifada HotelOS tizimini boshqaradigan uchta asosiy algoritm "
        "loyihalashtirilgan, blok-sxema bilan tavsiflangan va asoslangan. So'ngra "
        "Python tilida yozilgan kodning manba kodidan bajarilishigacha bo'lgan "
        "to'rt bosqichli yo'li va tanlangan texnologiya stekining asoslari "
        "keltirilgan. Algoritm tavsiflari to'g'ridan-to'g'ri "
        "reception_service/algorithms.py va maintenance_service/priority_queue.py "
        "modullariga mos keladi.",
    )

    # === 1.1 Xona Tayinlash Algoritmi ===
    add_heading(doc, "1.1 Xona Tayinlash Algoritmini Loyihalash", level=2)
    add_para(
        doc,
        "Xona tayinlash algoritmi tizimning yuragi hisoblanadi. Reception "
        "Servisning /checkin endpointiga kelgan har bir so'rovda bu algoritm 120 "
        "ta xonali inventardan ko'p mezonli filtrlash va saralash orqali eng "
        "mos xonani aniqlaydi. Mezonlar ketma-ket emas, balki ustun tartibida "
        "qo'llaniladi: bittasi muvaffaqiyatsiz bo'lsa, algoritm fallback "
        "qoidalariga o'tadi yoki to'g'ri xato qaytaradi.",
    )
    add_heading(doc, "Bosqichma-bosqich tavsif", level=3)
    add_para(
        doc,
        "Algoritm beshta mezonni quyidagi tartibda qo'llaydi. Har bir bosqich "
        "audit jurnalga reasoning matni sifatida qayd etiladi — bu xolatlarni "
        "qayta tiklash va xato izlashda foydali (Hunt va Thomas, 2000).",
    )
    add_para(
        doc,
        "Birinchidan, Mezon-1 (turi mosligi) qattiq filtr bo'lib, mehmon bron "
        "qilgan room_type qiymatiga teng bo'lmagan barcha xonalarni chiqarib "
        "tashlaydi. Agar bu bosqichdan keyin to'plam bo'sh bo'lsa, algoritm "
        "NoRoomAvailableError istisno tashlaydi — fallback yo'q, chunki Suite "
        "buyurtma qilgan mehmonga Single xona tayinlash xizmat sifatini "
        "buzadi.",
    )
    add_para(
        doc,
        "Ikkinchidan, Mezon-2 (tozalik) faqat status == CLEAN bo'lgan xonalarni "
        "qoldiradi. DIRTY, CLEANING, OCCUPIED yoki MAINTENANCE holatidagi "
        "xonalarning hech biri tayinlash uchun mos kelmaydi. Bu chekli holat "
        "ishonchli ravishda tekshiriladi: agar inventarda turi mos kelgan, "
        "lekin tozalanmagan xona bo'lsa, algoritm 'toza xona yo'q' xatosini "
        "qaytaradi.",
    )
    add_para(
        doc,
        "Uchinchidan, Mezon-3 (qavat afzalligi) mehmonning preferred_floor "
        "qiymati berilgan bo'lsa, faqat shu qavatdagi xonalarni qoldiradi. "
        "Agar bu qavatda hech qanday mos xona bo'lmasa, algoritm to'liq toza "
        "xonalar to'plamiga fallback qiladi — chunki brif aniq aytadi: 'agar "
        "o'sha qavatda mavjud xona bo'lmasa, istalgan mos qavatga o'ting'.",
    )
    add_para(
        doc,
        "To'rtinchidan, qolgan to'plam status_changed_at qiymati bo'yicha "
        "o'sib boruvchi tartibda tartiblanadi. Bu 'eng uzoq toza birinchi' "
        "siyosatini amalga oshiradi: xonalar ishlatilishi tekis aylantirib "
        "olinadi va bir xil xonalar qayta-qayta band qilinmaydi.",
    )
    add_para(
        doc,
        "Beshinchidan, Mezon-4 (yaqinlik) yakuniy hal qiluvchi tiebreaker. "
        "Agar proximity == LIFT bo'lsa, near_lift == True bo'lgan xonalarning "
        "tartiblangan to'plamidan birinchisi tanlanadi. Yaqinlikka mos xona "
        "topilmasa, mezon shunchaki o'tkazib yuboriladi va tartiblangan "
        "to'plamning birinchi elementi qaytariladi.",
    )

    add_heading(doc, "Blok-sxema", level=3)
    add_image(doc, DOCS / "diagram_room_assignment.png",
              "1-Rasm: Xona tayinlash algoritmi (assign_room) blok-sxemasi. Yashil — "
              "boshlash/tugatish, ko'k — jarayon, sariq — qaror, qizil — xato chiqishi.",
              width_cm=16)

    add_heading(doc, "Tanlangan yondashuvning asoslash", level=3)
    add_para(
        doc,
        "Bu algoritmni loyihalashda bir nechta alternativani ko'rib chiqdim. "
        "Birinchi alternativa har bir mezon uchun og'irlik berilgan ball "
        "tizimi edi (har bir xona uchun bal hisoblanib eng yuqori bal egasi "
        "tanlanadi). Bu yondashuvni rad etdim, chunki BTEC darajasidagi loyiha "
        "uchun tushuntirish murakkablashadi va 'qaysi mezon nima uchun "
        "qo'llanildi' degan savolga aniq javob bermaydi. Hozirgi ustun-tartibli "
        "filtrlash audit jurnali (reasoning ro'yxati) orqali har bir qarorni "
        "kuzatuvchan qiladi.",
    )
    add_para(
        doc,
        "Ikkinchi alternativa SQL ko'rinishida deklarativ so'rov edi (ORDER BY "
        "va WHERE bilan). Buni rad etdim, chunki mikroservis arxitekturada "
        "har bir servis o'z holatini boshqaradi va markaziy ma'lumotlar "
        "bazasiga bog'liqlik servislarni qattiq biriktiradi (Newman, 2021). "
        "Hozirgi Python implementatsiyasi sof funktsiya bo'lib, izolyatsiyada "
        "test qilinishi mumkin (test_algorithms.py 9 ta birlik testi bilan).",
    )

    # === 1.2 ===
    add_heading(doc, "1.2 Qo'shimcha Algoritmlarni Aniqlash va Loyihalash", level=2)
    add_heading(doc, "Hisob-kitob algoritmi", level=3)
    add_para(
        doc,
        "Check-outda calculate_bill() funksiyasi mehmonning umumiy hisobini "
        "to'rt qismdan yig'adi: xona to'lovi (nightly_rate × nights), xona "
        "xizmati buyurtmalarining yig'indisi, qo'shimcha to'lovlar (minibar, "
        "kech check-out 25.00) va chegirma. Decimal aniqligi ROUND_HALF_UP "
        "yaxlitlash bilan 0.01 oraliqda saqlanadi — float emas, chunki "
        "moliyaviy hisob-kitobda float aniqligi yetarli emas (McConnell, "
        "2004).",
    )
    add_para(
        doc,
        "Chegaraviy holatlar aniq boshqariladi. Erta check-out: agar "
        "actual_checkout vaqti berilsa, kun farqi olinadi va minimum 1 tun "
        "saqlanadi (mehmon kelgan kunining o'zida ketsa ham). Chegirma 0–100% "
        "oralig'idan chiqsa, ValueError tashlanadi — bu noto'g'ri "
        "konfiguratsiyani sukut bilan o'tkazib yubormaydi. Nol to'lovlar "
        "(masalan, hech qanday xona xizmati buyurtmasi) Decimal('0') boshlang'ich "
        "qiymati orqali tabiiy ravishda qo'llab-quvvatlanadi.",
    )
    add_image(doc, DOCS / "diagram_billing.png",
              "2-Rasm: Hisob-kitob algoritmi (calculate_bill) blok-sxemasi.",
              width_cm=14)

    add_heading(doc, "Texnik xizmat ustuvorlik navbat algoritmi", level=3)
    add_para(
        doc,
        "Maintenance Service kelayotgan muammolarni shoshilinchlik darajasi "
        "bo'yicha (Kritik, Yuqori, Normal, Past) tartiblashi va navbatdagi "
        "mavjud texnikka tayinlashi kerak. Brief talabi: agar ikki so'rov bir "
        "xil shoshilinchlikka ega bo'lsa, avval topshirilgani ustunlik oladi. "
        "Bu standart min-heap'ning ustida FIFO tiebreaker qatlamini talab "
        "qiladi.",
    )
    add_para(
        doc,
        "Amalga oshirishda Python'ning heapq moduli ishlatilgan. Heap kalit — "
        "uchta elementdan iborat tuple: (priority_value, sequence_number, "
        "issue_id). priority_value IssueUrgency.priority_value() metodidan "
        "olinadi (CRITICAL=0, HIGH=1, NORMAL=2, LOW=3 — past raqam yuqori "
        "ustuvorlik). sequence_number itertools.count() orqali atomar tarzda "
        "hosil qilinadi va FIFO tartibni ta'minlaydi. issue_id yakuniy "
        "deterministik solishtirish uchun. Push va pop operatsiyalari O(log "
        "n) murakkablikda ishlaydi (Aho va boshq., 1987).",
    )
    add_image(doc, DOCS / "diagram_priority_queue.png",
              "3-Rasm: Texnik xizmat ustuvorlik navbati algoritmi va misol kuzatuv.",
              width_cm=16)

    add_para(
        doc,
        "Algoritmning to'g'riligi tests/test_priority_queue.py da besh test "
        "bilan qoplangan, jumladan murakkab aralash holatlar: olti so'rov turli "
        "ustuvorliklarda kiritildi va kutilgan tartib (Critical FIFO → High "
        "FIFO → Normal → Low) bo'yicha chiqdi. scripts/demo_algorithms.py "
        "ishga tushirilganda bu kuzatuv real chiqish bilan ko'rsatildi (qarang: "
        "docs/demo_output.txt).",
    )

    # === 1.3 ===
    add_heading(doc, "1.3 Koddan Bajarilishgacha — Python Ish Vaqti", level=2)
    add_para(
        doc,
        "HotelOS Python 3.11+ tilida yozilgan. Python gibrid til — kompilyatsiya "
        "va interpretatsiya ikkalasini ham foydalanadi (Python Software "
        "Foundation, 2024). Manba kodimning bajarilgunga qadar bosqichlari "
        "quyidagicha kechadi.",
    )
    add_heading(doc, "1-bosqich: Oldindan qayta ishlash", level=3)
    add_para(
        doc,
        "Python an'anaviy ma'noda alohida preprocessor bosqichiga ega emas. "
        "Lekin import bayonotlari kompilyatsiyadan oldin hal qilinadi: kompilyator "
        "from shared.broker import MessageBroker yozilganini ko'rganda, "
        "shared/broker.py faylini topib uni yuklaydi. Bizning loyihamizda "
        "shared/ paketi uchun __init__.py fayllari bor — Python ularsiz "
        "paketni topa olmaydi.",
    )
    add_heading(doc, "2-bosqich: Kompilyatsiya bayt-kodga", level=3)
    add_para(
        doc,
        "python3 -m reception_service.main buyrug'ini ishga tushirganimda, "
        "CPython interpretatori har bir .py faylini bayt-kodga (.pyc fayllariga "
        "__pycache__ papkasida) kompilyatsiya qiladi. Bu bosqichda sintaksis "
        "xatolari aniqlanadi — masalan, ushlanmagan qavslar yoki noto'g'ri "
        "chekinish darhol SyntaxError bilan to'xtatadi. Loyihada Pydantic "
        "model dekoratorlari va type hint'lari ham ushbu bosqichda qisman "
        "tekshiriladi (lekin to'liq tip tekshiruvi yo'q — Python dinamik "
        "tipli).",
    )
    add_heading(doc, "3-bosqich: Bog'lash va bog'liqliklar", level=3)
    add_para(
        doc,
        "Python skompilyatsiya qilingan tildan farqli, alohida bog'lash "
        "bosqichiga ega emas. O'rniga bog'liqliklar runtime'da hal qilinadi. "
        "FastAPI, Pydantic, Redis va boshqa paketlar pip orqali virtual "
        "muhitga o'rnatiladi (requirements.txt bilan), so'ng Python import "
        "qilganda ularning .py va .so (C-extension) fayllarini topadi. "
        "Bizning README.md bog'liqliklarni quyidagicha o'rnatishni ko'rsatadi: "
        "pip install -r requirements.txt.",
    )
    add_heading(doc, "4-bosqich: Bajarish", level=3)
    add_para(
        doc,
        "Bajarish jarayoni uvicorn ASGI serverini ishga tushirish bilan "
        "boshlanadi. uvicorn FastAPI ilovasini import qiladi, lifespan kontekst "
        "menejerini ochadi (broker ulanishi, obunalar), so'ng HTTP/WebSocket "
        "so'rovlarini tinglaydi. Python ish vaqti muhiti referens hisoblash "
        "asosida xotirani boshqaradi va davriy generational garbage collector "
        "ishga tushiradi. Asyncio event loop bir thread'da minglab parallel "
        "korutinlarni boshqaradi — bu mikroservis uchun ideal, chunki I/O ko'p "
        "ishlatiladi (broker, HTTP, WebSocket).",
    )

    # === 1.4 ===
    add_heading(doc, "1.4 Texnologiya Stekini Asoslash", level=2)
    rows = [
        ["Python 3.11+", "Tezda prototip qilish, keng kutubxonalar ekotizimi, "
         "BTEC darajasida assessor uchun o'qish oson; cheklov: GIL — lekin "
         "bizning I/O-bog'liq ishimizda asyncio orqali yetarlicha samaradorlik."],
        ["FastAPI 0.115", "Avtomatik OpenAPI hujjati, Pydantic asosida tip "
         "tekshiruvi, WebSocket qo'llab-quvvatlash; alternativa Flask edi, "
         "ammo asinxron qo'llab-quvvatlash zaifroq."],
        ["Redis Pub/Sub", "Yengil, korporativ darajada sinovdan o'tgan, "
         "RabbitMQga nisbatan oson sozlash; alternativa NATS edi, ammo Redis "
         "ko'proq tanish va Docker bilan bir buyruqda ishlaydi."],
        ["FastAPI WebSocket", "Tashqi kutubxona kerak emas, JWT bilan birga "
         "ishlaydi; alternativa Socket.IO edi, ammo undagi qo'shimcha "
         "abstraksiya BTEC namoyishi uchun ortiqcha."],
        ["Pydantic v2", "Tezroq validatsiya (Rust asosida), Python tip "
         "hint'lari bilan to'liq mosligi."],
        ["Vanilla JS + Tailwind CDN", "Build qadami yo'q, deploy oson; "
         "alternativa React edi, lekin BTEC frontendga e'tibor kam — "
         "asosiy maqsad real vaqtli yangilanishni ko'rsatish."],
    ]
    add_table(doc, ["Komponent", "Tanlash sababi va cheklovlari"], rows,
              col_widths_cm=[5, 11])
    add_table_caption(doc, "1-Jadval: HotelOS texnologiya stekini asoslash")
