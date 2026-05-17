"""4-Vazifa kontenti — disk raskadrovka va kodlash standartlari."""

from scripts.generate_report import (
    add_code,
    add_heading,
    add_para,
    add_placeholder_screenshot,
    add_table,
    add_table_caption,
    page_break,
)


def task4(doc):
    page_break(doc)
    add_heading(doc, "4-Vazifa — Disk Raskadrovka va Kodlash Standartlari (LO4)", level=1)

    # === 4.1 Debug jarayoni ===
    add_heading(doc, "4.1 Disk Raskadrovka Jarayoni", level=2)
    add_para(
        doc,
        "Disk raskadrovka — dasturdagi xatti-harakatlarni sababini topish va "
        "tuzatish jarayoni. U ixtiyoriy keyingi fikr emas, balki dasturiy "
        "ta'minotni ishlab chiqishning zarur qismidir. Sababi oddiy: hech qanday "
        "muhim tizim birinchi yozuvda mukammal ishlamaydi. McConnell (2004) "
        "tahlilicha, professional dasturchilar ish vaqtlarining 30-50% ini "
        "disk raskadrovkaga sarflaydilar; HotelOS qurilishida bu nisbat shu "
        "darajada bo'ldi, ayniqsa asinxron broker va konkurrent test "
        "stsenariylarida.",
    )
    add_heading(doc, "Xato turlari", level=3)
    add_para(
        doc,
        "Sintaksis xatosi — kod Python grammatik qoidalarini buzadi va "
        "interpretator uni bayt-kodga aylantira olmaydi. Misol: HotelOS "
        "ishlab chiqishda dashboard_service/main.py da 'async def' "
        "o'rniga 'asnyc def' deb yozildi — interpretator darhol "
        "SyntaxError tashladi. Bu turdagi xato eng tez aniqlanadi: kod "
        "umuman ishga tushmaydi.",
    )
    add_para(
        doc,
        "Ishlash xatosi (runtime error) — kod kompilyatsiya bo'ladi, lekin "
        "bajarish davomida istisno tashlanadi. Misol: birinchi versiyada "
        "_post_charge_to_reception() funksiyasi httpx.HTTPError'ni "
        "tutmadi va Reception servisi ishlamayotganda Room Service crash "
        "qilardi. Bu KeyError, TypeError, ConnectionError kabi xatolardan "
        "iborat.",
    )
    add_para(
        doc,
        "Mantiq xatosi — kod ishlaydi va istisno tashlamaydi, lekin noto'g'ri "
        "natija beradi. Bu eng yashirin tur. Misol: dastlabki priority_queue "
        "amalga oshirishida sequence_number yo'q edi va bir xil ustuvorlikdagi "
        "elementlar deterministik tartibda chiqmas edi (qarang: 4.2-bo'lim, "
        "XATO-02).",
    )
    add_heading(doc, "IDE'dagi disk raskadrovka vositalari", level=3)
    add_para(
        doc,
        "VS Code Python debugger to'rt asosiy vositani taklif etadi. To'xtash "
        "nuqtalari (F9) — kodning ma'lum qatorida bajarishni to'xtatadi, "
        "shunda kontekstni tekshirish mumkin. Kuzatuv ifodalari — bajarish "
        "davom etganda o'zgaruvchi yoki ifoda qiymatini avtomatik kuzatadi "
        "(masalan, len(queue._heap) ni har bir to'xtashda yangilab turish). "
        "Chaqiruv steki — qaysi funksiyalar qaysi tartibda chaqirilganini "
        "ko'rsatadi (asyncio coroutine'lar uchun ham). Bosqichma-bosqich "
        "bajarish (F10/F11) — kodni bir qatorda yoki funksiyaga kirib o'tish "
        "imkonini beradi.",
    )
    add_heading(doc, "Umumiy disk raskadrovka ish jarayoni", level=3)
    add_para(
        doc,
        "Tushunmagan xatoga qanday yondashaman? Birinchi bosqich — xatoni "
        "qayta hosil qilish. Agar mening kompyuterimda muvaffaqiyatli qayta "
        "hosil qilolmasam, men uni tuzatolmayman. Ikkinchi bosqich — eng "
        "yaqin to'xtash nuqtasini xato joyiga qo'yish va bajarish, kontekstni "
        "tekshirish (o'zgaruvchilar qiymatlari, chaqiruv steki, faol "
        "korutinlar). Uchinchi bosqich — orqaga yo'naltirish: qaysi qator "
        "yoki funksiya noto'g'ri holatni hosil qildi? To'rtinchi bosqich — "
        "tuzatish, so'ng test bilan tasdiqlash (regression test qo'shish). "
        "Beshinchi bosqich — git commit'da xato va tuzatish izohi.",
    )

    # === 4.2 Debug jurnali — 3 ta xato ===
    add_heading(doc, "4.2 Disk Raskadrovka Jurnali — Uchta Haqiqiy Xato", level=2)
    add_para(
        doc,
        "Quyida HotelOS ishlab chiqish davomida duch kelgan va tuzatgan uchta "
        "haqiqiy xato hujjatlashtirilgan. Kamida bittasi konkurrentlik / vaqt "
        "muammosini o'z ichiga oladi (brief talabi).",
    )

    add_heading(doc, "XATO-01: room.vacated obunasi xabarni o'tkazib yuborardi", level=3)
    rows = [
        ["Xato ID", "XATO-01"],
        ["Tavsif",
         "Reception servisi check-out qilganda room.vacated nashr etardi, lekin "
         "Housekeeping ba'zan xabarni qabul qilmasdi. Test stsenariy TS-02 ning "
         "ikkinchi qismi (xonani tozalash navbatiga qo'shish) muvaffaqiyatsiz "
         "bo'lardi taxminan har 5-urunishidan 1tasida."],
        ["Turi", "Ishlash xatosi (timing/race condition)"],
        ["Qanday aniqlandi",
         "TS-02 avtomatlashtirilgan testi noaniq muvaffaqiyatsiz bo'lardi. Qo'lda "
         "qayta hosil qilish qiyin edi — har bir uzilgan urunish dispatchni "
         "boshqacha tartiblardi. logs/housekeeping.log da xabar hech qachon "
         "ko'rinmasdi."],
        ["Disk raskadrovka qadamlari",
         "1. Housekeeping main.py'da broker.subscribe(EVT_ROOM_VACATED, ...) "
         "qatoriga to'xtash nuqtasi qo'yildi va testni ishga tushirdim. To'xtash "
         "nuqtasiga umuman tushmadi! Demak obuna asyncio.create_task() chaqirig'i "
         "ishga tushgunga qadar amalga oshmagan edi. "
         "2. lifespan() async kontekstida obunalar listener vazifasidan oldin "
         "ulanishi kerakligini aniqladim — ammo birinchi versiyada subscribe() "
         "create_task() dan KEYIN yozilgan edi. "
         "3. Tartib yangilandi: avval subscribe, keyin start_listening()."],
        ["Asosiy sabab",
         "lifespan() ichida await broker.start_listening() listener task'ini "
         "asyncio.create_task() bilan ishga tushirilgan, lekin .subscribe() "
         "chaqiriqlari yetkazilmasdan turib listener boshlana boshlagan. Birinchi "
         "kelgan room.vacated xabar hech qaysi handler bilan bog'lanmagan."],
        ["Qo'llanilgan tuzatish",
         "lifespan() ichida tartib o'zgartirildi: avval broker.connect(), so'ng "
         "BARCHA broker.subscribe() chaqiriqlari, va FAQAT shundan keyin "
         "asyncio.create_task(broker.start_listening()). Bu yumshoq, lekin aniq: "
         "obunalar har doim listener'dan oldin amalga oshiriladi."],
        ["Oldini olish",
         "Kelajakda lifespan boshqa servislar uchun template sifatida ishlatiladi: "
         "1) connect, 2) subscribe-all, 3) create listener task — yagona "
         "tartib. Qo'shimcha himoya sifatida InMemoryBroker InMemoryBroker'da "
         "obuna ro'yxati Lock bilan o'ralgan."],
    ]
    add_table(doc, ["Maydon", "Tafsilot"], rows, col_widths_cm=[3.5, 12.5])

    add_heading(doc, "XATO-02: bir xil ustuvorlikdagi muammolarning noaniq tartibi (RACE/TIMING)", level=3)
    rows = [
        ["Xato ID", "XATO-02"],
        ["Tavsif",
         "TS-05 stsenariysi past ustuvorlikdagi muammo birinchi kiritilib, "
         "so'ng kritik kiritilgani sinab ko'rilardi. Kutilgan: kritik birinchi "
         "chiqishi. Real natija: ba'zida kritik, ba'zida past birinchi chiqardi. "
         "Bundan tashqari, ikki bir xil ustuvorlikdagi muammo ham noaniq "
         "tartibda chiqardi."],
        ["Turi", "Mantiq xatosi + konkurrentlik (race-style)"],
        ["Qanday aniqlandi",
         "tests/test_priority_queue.py'da test_fifo_within_same_urgency testi "
         "muvaffaqiyatsiz bo'ldi. Ishlab chiquvchi test 1000 marta ishga "
         "tushirilganda har xil natijalar oldi."],
        ["Disk raskadrovka qadamlari",
         "1. heapq.heappush() chaqirig'iga to'xtash nuqtasi qo'yildi va _heap "
         "ichidagi entry tuple'lari ko'rildi. Birinchi versiyada kalit (priority, "
         "issue_id) edi — sequence yo'q edi. "
         "2. Python uuid'lari leksikografik tartiblanganda kiritish tartibiga mos "
         "kelmaydi (UUID4 random) — shuning uchun bir xil ustuvorlikdagi "
         "elementlar tasodifiy tartibda chiqar edi. "
         "3. Hatto bir xil mashinada konkurrent .push() chaqiriqlari turli "
         "tartibga olib kelishi mumkin edi."],
        ["Asosiy sabab",
         "Min-heap algoritmi tiebreaker sifatida ikkinchi kalitni ishlatadi. "
         "Bizning birinchi versiyada ikkinchi kalit issue_id (UUID hex satr) "
         "edi — bu kiritish tartibi bilan bog'liq emas. FIFO ta'minlanmas edi."],
        ["Qo'llanilgan tuzatish",
         "itertools.count() asosida global atomar hisoblagich qo'shildi. Heap "
         "kalit (priority, sequence, issue_id) — bu yerda sequence "
         "monotonik o'sib boruvchi va konkurrent .push() chaqiruvlari uchun ham "
         "deterministik. itertools.count() Python ichida thread-safe (GIL "
         "kafolatlari ostida)."],
        ["Oldini olish",
         "Tiebreaker'lar har doim deterministik bo'lishi kerak. Yangi test "
         "qo'shildi: 1000 marta push/pop tsikli bir xil natija beradi. Ushbu "
         "namuna boshqa konkurrent ma'lumotlar tuzilmalariga qo'llaniladi."],
    ]
    add_table(doc, ["Maydon", "Tafsilot"], rows, col_widths_cm=[3.5, 12.5])

    add_heading(doc, "XATO-03: Decimal ↔ float aralashishi noto'g'ri hisobga olib keldi", level=3)
    rows = [
        ["Xato ID", "XATO-03"],
        ["Tavsif",
         "test_calculate_bill testi tasodifan muvaffaqiyatsiz bo'ldi: kutilgan "
         "net_total='481.95' edi, lekin haqiqiy '481.94999999...' chiqardi. "
         "Bunday kichik xato yashirin bo'lardi, ammo moliyaviy hisob-kitobda "
         "qabul qilinmaydi."],
        ["Turi", "Mantiq xatosi (floating-point aniqligi)"],
        ["Qanday aniqlandi",
         "pytest'da kutilgan/haqiqiy taqqoslash muvaffaqiyatsiz. Skripda "
         "konsolga chiqarganda 50 dan ortiq raqamli quyruq ko'rindi."],
        ["Disk raskadrovka qadamlari",
         "1. calculate_bill() ichiga print(type(gross_total), gross_total) qo'shildi. "
         "Chiqish ikki xil turini ko'rsatdi: ba'zilari Decimal, ba'zilari float. "
         "2. Sababi: menu.json'dan o'qilgan narxlar float edi (JSON Decimal "
         "qo'llab-quvvatlamaydi), so'ng arifmetik amal Decimal'ni float'ga "
         "majburlardi. "
         "3. Asoslangan tekshiruvlar: 0.1 + 0.2 IEEE 754 floatda 0.3 emas — "
         "moliyaviy kod uchun Decimal majburiy (McConnell, 2004)."],
        ["Asosiy sabab",
         "JSON loader narxlarni float sifatida o'qiydi. Birinchi versiyada "
         "RoomServiceOrder.total maydoni Decimal sifatida deklaratsiya "
         "qilingan, lekin order.total kalkulatsiyasi float arifmetikada "
         "bajarilgan."],
        ["Qo'llanilgan tuzatish",
         "Menu yuk qilinganda Decimal(str(item['price'])) ga aylantirish (str() "
         "muhim — float'dan to'g'ridan-to'g'ri Decimal kerakli aniqlikni "
         "saqlamaydi). Pydantic v2'da @field_validator orqali kelgan float "
         "qiymatlarini Decimal'ga aylantirish."],
        ["Oldini olish",
         "Pul yoki narx bilan bog'liq har qanday maydon Decimal sifatida "
         "deklaratsiya qilinadi va float bilan aralashtirilmaydi. Yangi "
         "koddagi qoidalar fayl boshidagi konstantalarga qo'yildi: "
         "ROUNDING_PLACES = Decimal('0.01')."],
    ]
    add_table(doc, ["Maydon", "Tafsilot"], rows, col_widths_cm=[3.5, 12.5])

    # === 4.3 Security debugging ===
    add_heading(doc, "4.3 Xavfsizlik uchun Disk Raskadrovka", level=2)
    add_para(
        doc,
        "Disk raskadrovka jarayoni HotelOSni xavfsizroq va ishonchli qildi. "
        "Bir konkret zaiflik ishlab chiqish davomida aniqlandi va tuzatildi: "
        "Dashboard servisining /state endpointi dastlab JWT token tekshiruvini "
        "qo'llamasdan to'liq holatni qaytarardi. Bu pasport raqamlari va "
        "to'lov ma'lumotlarini kim xohlasa olishi mumkin bo'lgan zaiflik edi.",
    )
    add_para(
        doc,
        "Zaiflikni qanday topdim: barcha brokerga yuborilgan yuklarni jurnal "
        "qilish vositasi (logger.debug) bilan WebSocket panelga uzatilayotgan "
        "ma'lumotlarni kuzatdim. Test tarmoqida curl bilan /state ga "
        "Authorization sarlavhasiz so'rov yubordim — javob keldi va guest "
        "ob'ektlari ichida document_id ko'rindi. Bu jiddiy ma'lumotlarni "
        "oshkor qilish (data exposure) zaifligi edi.",
    )
    add_para(
        doc,
        "Kodda aynan qaerda mavjudligini topish uchun: VS Code'da Pylance "
        "'Find All References' (Shift+F12) bilan /state endpointini topdim, "
        "so'ng Depends(bearer_scheme) chaqirig'i yo'qligini ko'rdim. Tuzatish: "
        "credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme) "
        "parametri qo'shildi va _verify_token() chaqirig'i bajarildi. Endi "
        "tokensiz so'rovga 401 javob keladi.",
    )
    add_para(
        doc,
        "Bundan tashqari, redact_sensitive() funksiyasi qo'shildi va u "
        "ConnectionManager.broadcast() ichida har bir yukga qo'llaniladi. Bu "
        "ikki qatlamli himoya: token tekshiruvi rad etsa ham, agar biron-bir "
        "xato yuzaga kelsa ham, maxfiy maydonlar maska bilan qoplangan.",
    )
    add_para(
        doc,
        "Xavfsizlik muammolarini ishlab chiqish davomida ushlash sezilarli "
        "darajada arzon. Production'da xuddi shu xatoning ta'siri: GDPR "
        "buzilishi, mehmonlar ishonchini yo'qotish, potentsial sud da'volari, "
        "regulyator jarimalari. Ishlab chiqish davomida tuzatish — bir nechta "
        "kod qatori, bir necha soat ish. Bu xulosa shaxsiy mehmon ma'lumotlarini "
        "boshqaradigan har qanday tizim uchun universal: xavfsizlik birinchi "
        "loyihalashda, keyin tekshirishda, va doimo ishlab chiqishda — deploy "
        "vaqtida emas (McConnell, 2004; Newman, 2021).",
    )

    # === 4.4 Coding standard ===
    add_heading(doc, "4.4 HotelOS Kodlash Standartingiz", level=2)
    add_para(
        doc,
        "HotelOS PEP 8 (Python rasmiy stil qo'llanmasi) bilan asoslangan, "
        "loyiha-maxsus kengaytmalar bilan to'ldirilgan kodlash standartini "
        "qo'llaydi. Standart pyproject.toml'da formal qoidalar (ruff, black) "
        "orqali avtomatik amalga oshiriladi.",
    )

    add_heading(doc, "Nomlash konventsiyalari", level=3)
    add_para(
        doc,
        "O'zgaruvchilar va funksiyalar — snake_case (PEP 8). Misol: room_number, "
        "calculate_bill(). Klasslar — PascalCase: RoomInventory, MessageBroker. "
        "Konstantalar — UPPER_SNAKE_CASE: LATE_CHECKOUT_FEE, MAX_ROOM_NUMBER. "
        "Fayl nomlari — snake_case: reception_service/main.py, priority_queue.py. "
        "Maxfiy/private a'zolar — bitta osti chiziq prefiks: ._lock, ._rooms.",
    )
    add_code(doc, '''# To'g'ri
class IssuePriorityQueue:           # PascalCase klass
    MAX_QUEUE_SIZE = 1000          # UPPER_SNAKE konstanta
    def __init__(self):
        self._heap = []            # private prefiks
        self._counter = itertools.count()
    def push(self, issue_id, urgency, data):  # snake_case
        ...''')

    add_heading(doc, "Izohlar va hujjatlashtirish", level=3)
    add_para(
        doc,
        "Har bir modul faylning yuqorisida modul docstring (uch tirnoq orasida) "
        "modulning mas'uliyatini izohlaydi. Har bir umumiy funksiya va klass "
        "docstring bilan ta'minlangan. Satr ichidagi izohlar 'nima qilayotganini' "
        "emas, 'nima uchun' kerakligini tushuntiradi (Fowler, 2018). Murakkab "
        "algoritmik bo'limlar batafsil izohlangan (masalan, assign_room()'da "
        "har bir mezon bosqichi).",
    )
    add_code(doc, '''def calculate_bill(booking, room_service_orders, ...):
    """Mehmon check-outda umumiy to'lovni hisoblaydi.

    Erta check-out: agar `actual_checkout` berilsa, bron qilingan tunlar
    o'rniga haqiqiy tunlar hisoblanadi (lekin minimum 1 tun).

    Returns: yorliqlangan bo'limlarga ega lug'at — auditga oson.
    """''')

    add_heading(doc, "Chekinish va formatlash", level=3)
    add_para(
        doc,
        "4 bo'shliq (tab emas) chekinishi PEP 8 bo'yicha. Maksimal qator "
        "uzunligi 100 belgi (pyproject.toml'da black va ruff orqali). Uzun "
        "qatorlar dumaloq qavslar ichida yumshatiladi: argument ro'yxati har "
        "biri yangi qatorda, oxirgi vergul bilan (trailing comma).",
    )

    add_heading(doc, "Funksiya va klass uzunligi", level=3)
    add_para(
        doc,
        "Funksiyalar uchun maksimal 50 qator (cyclomatic complexity 10 — "
        "ruff sozlamasi). assign_room() funksiyasi 60 qator yaqin keldi va "
        "Mezon-4 mantiqi alohida yordamchi funksiyaga ajratilishi mumkin "
        "edi — lekin bu nuqtada algoritm ravon o'qiladi va ajratish "
        "kontekstni buzgan bo'lardi. Bu BTEC darajasidagi kompromiss "
        "(McConnell, 2004).",
    )

    add_heading(doc, "Xatolarni boshqarish", level=3)
    add_para(
        doc,
        "Try/except bloklari faqat aniq istisno turlari uchun. Har qanday "
        "Exception ni ushlash (bare except) taqiqlangan — bu xato yo'qotishga "
        "olib keladi. Tuzatib bo'lmaydigan xatolar ko'tariladi (re-raise) "
        "yoki logger.exception() bilan yoziladi. Foydalanuvchi tomonidagi "
        "xato xabarlari hech qachon ichki stek izini oshkor qilmaydi.",
    )
    add_code(doc, '''# Yomon — keng tarqalgan antipattern
try:
    do_something()
except Exception:
    pass

# Yaxshi — aniq istisno + jurnal + qayta tashlash
try:
    do_something()
except ValidationError as exc:
    logger.warning("Validation failed: %s", exc)
    raise HTTPException(status_code=400, detail=str(exc)) from exc''')

    add_heading(doc, "Sehrli raqamlar va konstantalar", level=3)
    add_para(
        doc,
        "Hech qaerda 'magic number' qo'llanilmaydi. Har qanday qattiq kodlangan "
        "qiymat nomlangan konstanta sifatida e'lon qilinadi (shared/security.py "
        "va reception_service/algorithms.py boshida). Bu kelajakda o'zgartirish "
        "uchun bir markaziy nuqta yaratadi va kodning niyatini ravshan qiladi.",
    )
    add_code(doc, '''# Yomon
if discount > 100: raise ValueError

# Yaxshi
DISCOUNT_MAX_PERCENT = Decimal("100")
if discount > DISCOUNT_MAX_PERCENT: raise ValueError''')

    # === 4.5 Why standards matter ===
    add_heading(doc, "4.5 Kodlash Standartlari Jamoada Nima Uchun Muhim", level=2)
    add_para(
        doc,
        "Kodlash standartining roli individual HotelOS loyihasidan tashqarida "
        "ham ulkan. Standartlar nafaqat yakka dasturchi uchun yaxshi amaliyot, "
        "balki professional jamoa muhitida mutlaqo zarur.",
    )
    add_para(
        doc,
        "Hech qanday standart tatbiq etilmagan kod bazasiga vaqt o'tishi bilan "
        "uch narsa sodir bo'ladi. Birinchidan, har bir dasturchi o'z uslubini "
        "joriy qiladi (kimdir snake_case, kimdir camelCase; kimdir 2 bo'shliq, "
        "kimdir 4 bo'shliq) va kod bazasi mozaikaga aylanadi. Ikkinchidan, "
        "har bir kod ko'rib chiqish sub'ektiv stil munozaralariga sarflanadi "
        "— mantiq emas, balki bo'shliqlar haqida bahslar. Uchinchidan, yangi "
        "jamoa a'zolari kirishish vaqti keskin oshadi: ular avval har bir "
        "modulning o'ziga xos uslubini o'rganishlari kerak (Hunt va Thomas, "
        "2000).",
    )
    add_para(
        doc,
        "Kodlash standarti yangi jamoa a'zolari uchun kirishish vaqtini bir "
        "necha haftadan bir necha kunga qisqartiradi. Yangi dasturchi PEP 8 + "
        "loyiha kengaytmalarini bilsa, har qanday Python fayl tanish ko'rinadi. "
        "Ular kodning shaklini emas, mantiqini o'rganishga e'tibor qaratadilar. "
        "Bu Newman'ning (2021) mikroservis kitobida ta'kidlangan: 'Conway's Law' "
        "loyiha tashkilotini kod tuzilishiga aks ettiradi — bir xil stil bir "
        "xil jamoa intelligentsini ifodalaydi.",
    )
    add_para(
        doc,
        "Avtomatlashtirilgan vositalar standartlarni qo'lda intizomga "
        "tayanmasdan amalga oshiradi. HotelOSda: ruff (linting + isort) "
        "stilistik muammolarni va xavfsizlik antipatternlarini qayd etadi; "
        "black (formatter) avtomatik ravishda bir xil formatlash hosil "
        "qiladi; pytest har bir push'da testlarni ishga tushiradi; pre-commit "
        "hook'lar majburiy gate sifatida ishlaydi. Avtomatlashtirilgan "
        "tekshiruvlar 100% izchillikni ta'minlaydi va inson xatosini "
        "yo'q qiladi.",
    )
    add_para(
        doc,
        "HotelOSga qo'llagan standartim professional jamoa uchun deyarli "
        "mos. Jamoa muhitiga ko'chirsam, qo'shgan bo'lar edim: (1) majburiy "
        "type-hint qoplama (mypy --strict), chunki dynamic Python katta "
        "loyihalarda noaniqlikka olib keladi; (2) Conventional Commits format "
        "git xabarlari uchun (feat:, fix:, refactor:), bu CHANGELOG "
        "avtomatik generatsiyaga imkon beradi; (3) majburiy code review "
        "kamida 1 ta tasdiqlovchi bilan; (4) docstring qoplama tekshiruvi "
        "(pydocstyle). HotelOSning hozirgi 14 ta birlik testi va dual broker "
        "amalga oshirishi bu kengaytmalar uchun mustahkam asos beradi.",
    )
