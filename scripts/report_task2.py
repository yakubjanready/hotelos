"""2-Vazifa kontenti — dasturlash paradigmalari."""

from scripts.generate_report import (
    add_code,
    add_heading,
    add_para,
    page_break,
)


def task2(doc):
    page_break(doc)
    add_heading(doc, "2-Vazifa — HotelOSda Dasturlash Paradigmalari (LO2)", level=1)
    add_para(
        doc,
        "HotelOS uchta asosiy dasturlash paradigmasini birlashtiradi. Quyida har "
        "birining ta'rifi, asosiy tamoyillari, HotelOS kodida qaerda paydo "
        "bo'lishi va nima uchun shu paradigmaning shu joyda eng mos kelishi "
        "tushuntirilgan. Barcha kod parchalari haqiqiy reception_service/, "
        "housekeeping_service/, dashboard_service/ fayllaridan olingan.",
    )

    add_heading(doc, "2.1 Uchta Paradigma Tushuntirildi", level=2)
    add_para(
        doc,
        "Protsedural dasturlash — kodni 'birinchi buni qil, keyin buni qil' "
        "tarzida bosqichli protseduralar yig'indisi sifatida tashkil etadi. "
        "Asosiy tamoyili — bajarish oqimi yuqoridan pastga, funksiya "
        "chaqiriqlari orqali. Ma'lumotlar protseduralarga argument sifatida "
        "uzatiladi va natija qaytariladi. Bu paradigma tabiiy ravishda chiziqli "
        "ish jarayonlari (masalan, hisob-kitob, kiritish tekshiruvi, fayldan "
        "yuklash) uchun mos keladi (McConnell, 2004).",
    )
    add_para(
        doc,
        "Ob'ektga yo'naltirilgan dasturlash (OOP) ma'lumot va xatti-harakatni "
        "birlashtiradi. To'rt ustun: inkapsulyatsiya (ichki holatni himoya "
        "qilish), meros olish (kodni qayta ishlatish), polimorfizm (bir interfeysning "
        "ko'p amalga oshirishlari) va abstraksiya (murakkablikni yashirish). "
        "OOP murakkab domen modellari (xonalar, mehmonlar, buyurtmalar) va "
        "uzoq muddatli holat boshqaruvi uchun ideal.",
    )
    add_para(
        doc,
        "Hodisaga asoslangan dasturlash kodning oqimini hodisalar belgilaydi: "
        "broker xabari, WebSocket ulanishi, foydalanuvchi harakati, taymer. "
        "Dastur 'so'rab olmaydi' (poll qilmaydi), balki 'xabar oladi' "
        "(reactive). Bu paradigma tarqalgan tizimlarda va real vaqtli "
        "yangilanishlarda ustun.",
    )
    add_para(
        doc,
        "Paradigmalar o'zaro inkor etmaydi. HotelOSda uchovi bir tizimda "
        "ishlatiladi: OOP domen modellarini ifodalaydi (Room, Booking, Guest), "
        "protsedural funksiyalar algoritmlarni amalga oshiradi (assign_room, "
        "calculate_bill), hodisaga asoslangan dizayn esa servislar o'rtasidagi "
        "muloqotni va panel yangilanishlarini boshqaradi. Bu kombinatsiya real "
        "dunyo dasturiy ta'minotida keng tarqalgan: har bir paradigma o'ziga "
        "xos muammoga eng mos vositadir.",
    )

    add_heading(doc, "2.2 HotelOSda Protsedural Dasturlash", level=2)
    add_para(
        doc,
        "Protsedural dasturlash HotelOSda eng aniq tarzda algoritm modullarida "
        "ko'rinadi. reception_service/algorithms.py faylining ikkala funksiyasi "
        "— assign_room() va calculate_bill() — sof procedurlardir: kirish "
        "olamiz, bosqichma-bosqich qayta ishlaymiz, natijani qaytaramiz, "
        "obyekt holati o'zgartirilmaydi.",
    )
    add_heading(doc, "1-misol: calculate_bill() — bosqichli hisoblash", level=3)
    add_para(
        doc,
        "Bu funksiya beshta bosqichni ketma-ket bajaradi: kiritishni tekshirish, "
        "tunlar sonini aniqlash, xona kichik-jamini, xizmat to'lovlarini va "
        "qo'shimcha to'lovlarni hisoblash, nihoyat chegirma qo'llash. Kod oqimi "
        "to'liq chiziqli — hech qanday OOP yoki hodisalar bilan aralashmagan.",
    )
    add_code(doc, '''def calculate_bill(booking, room_service_orders, minibar_charge=Decimal("0"),
                   late_checkout=False, discount_percent=Decimal("0"), actual_checkout=None):
    # 1-bosqich: validation
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Chegirma 0–100% oralig'ida bo'lishi kerak")

    # 2-bosqich: tunlar sonini aniqlash (erta check-out)
    nights = booking.nights
    if actual_checkout and booking.check_in_at:
        actual = max(1, (actual_checkout - booking.check_in_at).days)
        nights = min(nights, actual)

    # 3-bosqich: kichik-jamilarni hisoblash
    room_subtotal = booking.nightly_rate_locked * nights
    service_subtotal = sum((o.total for o in room_service_orders), start=Decimal("0"))
    extras = booking.extra_charges + minibar_charge
    if late_checkout:
        extras += LATE_CHECKOUT_FEE

    # 4-bosqich: yig'indi va chegirma
    gross_total = room_subtotal + service_subtotal + extras
    discount = (gross_total * discount_percent / Decimal("100")).quantize(...)
    net_total = (gross_total - discount).quantize(...)

    return { ... }   # yorliqlangan bo'limli lug'at''')
    add_para(
        doc,
        "Bu yerda protsedural yondashuv to'g'ri tanlov, chunki: (1) hisob-kitob "
        "matematik formula, ob'ekt holati emas; (2) funksiya stateless — bir "
        "xil kirish doim bir xil chiqish hosil qiladi (test qilish oson); (3) "
        "OOP klass yaratish ortiqcha boilerplate qo'shgan bo'lardi (Hunt va "
        "Thomas, 2000).",
    )

    add_heading(doc, "2-misol: input validation protsedurasi", level=3)
    add_para(
        doc,
        "shared/security.py dagi InputValidator klassi protsedurali yondashuvni "
        "qo'llaydi — barcha metodlari @classmethod va shartli sof funksiyalardir.",
    )
    add_code(doc, '''@classmethod
def validate_room_number(cls, value):
    try:
        room = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Xona raqami butun son bo'lishi kerak: {value!r}") from exc
    if not (MIN_ROOM_NUMBER <= room <= MAX_ROOM_NUMBER):
        raise ValidationError(f"Xona raqami {MIN_ROOM_NUMBER}–{MAX_ROOM_NUMBER} oralig'ida bo'lishi kerak")
    return room''')
    add_para(
        doc,
        "Validatsiya tabiiy ravishda protsedural: 'bu shartlarni tekshir, "
        "muvaffaqiyatsiz bo'lsa istisno tashla, aks holda toza qiymatni "
        "qaytar'. Bu yerda hech qanday holat saqlanmaydi va meros olish "
        "yoki polimorfizm hech qanday ishtirok etmaydi.",
    )

    # === 2.3 OOP ===
    add_heading(doc, "2.3 HotelOSda Ob'ektga Yo'naltirilgan Dasturlash", level=2)
    add_heading(doc, "Inkapsulyatsiya: RoomInventory klassi", level=3)
    add_para(
        doc,
        "reception_service/main.py dagi RoomInventory klassi ichki "
        "ma'lumotlarini (._rooms dict, ._lock RLock) to'g'ridan-to'g'ri "
        "tashqi kirishdan himoyalaydi. Tashqi kod faqat .all_rooms(), .get(), "
        ".update_status() metodlari orqali xonalarga kirishi mumkin. Bu HotelOS "
        "uchun muhim, chunki bir vaqtning o'zida bir nechta check-in so'rovi "
        "kelishi mumkin (TS-06 stsenariysi) va inventarni o'zgartirish thread-"
        "safe bo'lishi kerak.",
    )
    add_code(doc, '''class RoomInventory:
    def __init__(self):
        self._rooms: dict[int, Room] = {}   # _ — "private" konventsiyasi
        self._lock = threading.RLock()       # bir vaqtning o'zida yangilanishlardan himoya

    def update_status(self, number, new_status):
        with self._lock:
            room = self._rooms[number]
            room.mark_status_changed(new_status)
            return room''')

    add_heading(doc, "Meros olish: Staff -> Receptionist, Housekeeper, Technician", level=3)
    add_para(
        doc,
        "shared/models.py dagi Staff klassi xodimlar uchun asosiy modelni "
        "belgilaydi (staff_id, full_name, role, on_duty). HotelOSda har bir "
        "xodim turi qo'shimcha xususiyatlarga ega bo'lishi mumkin (masalan, "
        "Technician — ixtisoslashuv, Housekeeper — joriy zona). Hozirgi "
        "amalga oshirishda role enum bilan farqlanadi, ammo arxitektura "
        "kelajakda ierarxiyaga osongina kengaytirilishi mumkin:",
    )
    add_code(doc, '''class Staff(BaseModel):
    """Xodim asosiy klassi — OOP meros olishi uchun asos."""
    staff_id: str
    full_name: str
    role: StaffRole
    on_duty: bool = True

# Kelajakdagi kengaytma (hozircha rejada):
class Technician(Staff):
    role: StaffRole = StaffRole.TECHNICIAN
    specialisations: list[str] = []
    current_assignment: str | None = None

class Housekeeper(Staff):
    role: StaffRole = StaffRole.HOUSEKEEPER
    assigned_floor: int | None = None''')

    add_heading(doc, "Polimorfizm: MessageBroker abstrakt klassi", level=3)
    add_para(
        doc,
        "shared/broker.py da MessageBroker abstrakt klassi belgilanadi. Ikki "
        "amalga oshirish (RedisBroker va InMemoryBroker) bir xil interfeysni "
        "qo'llaydi. Yuqori darajadagi kod (reception, housekeeping, va h.k.) "
        "qaysi konkret klass ishlatilayotganini bilmaydi — u faqat .publish() "
        "va .subscribe() metodlarini chaqiradi. Bu test rejimida InMemoryBroker'ga "
        "almashish va ishlab chiqarishda Redis'ni saqlab qolishni osonlashtiradi.",
    )
    add_code(doc, '''class MessageBroker(ABC):
    @abstractmethod
    async def publish(self, topic: str, payload: dict) -> None: ...
    @abstractmethod
    async def subscribe(self, topic: str, handler: EventHandler) -> None: ...

class RedisBroker(MessageBroker):
    async def publish(self, topic, payload):
        await self._client.publish(topic, json.dumps(payload, default=str))

class InMemoryBroker(MessageBroker):
    async def publish(self, topic, payload):
        await self._queue.put((topic, payload))''')

    add_heading(doc, "Abstraksiya: assign_room() bitta chaqiriqdagi murakkablik", level=3)
    add_para(
        doc,
        "Reception servisining /checkin endpointini chaqiruvchi mijoz beshta "
        "mezonni qanday filtrlash, qanday tartiblash va qanday tiebreaker "
        "qo'llash haqida hech narsa bilishi shart emas. assign_room(inventory, "
        "type, floor, proximity) chaqirig'i hammasini abstraktlashtiradi. Bu "
        "yashirish darajasi sayqallangan modullarni boshqalardan ajratadi va "
        "test qilishni osonlashtiradi.",
    )

    add_heading(doc, "2.4 HotelOSda Hodisaga Asoslangan Dasturlash", level=2)
    add_heading(doc, "1-misol: room.vacated hodisasi broker orqali", level=3)
    add_para(
        doc,
        "Mehmon check-out qilganda, Reception servisi room.vacated hodisasini "
        "Redis Pub/Sub'ga nashr etadi. Housekeeping servisi ushbu mavzuga "
        "obuna bo'lib turibdi va hodisani qabul qilganda xonani tozalash "
        "navbatiga avtomatik qo'shadi. Reception kim tinglayotganini bilmaydi "
        "— bu loose coupling tamoyili (Newman, 2021).",
    )
    add_code(doc, '''# Reception (publisher):
await broker.publish(
    EVT_ROOM_VACATED,
    {
        "room_number": booking.room_number,
        "previous_guest": guest.public_view(),
        "timestamp": booking.check_out_at.isoformat(),
    },
)

# Housekeeping (subscriber):
async def on_room_vacated(topic: str, payload: dict) -> None:
    number = InputValidator.validate_room_number(payload.get("room_number"))
    queue.enqueue(number)
    logger.info("Hodisa qabul qilindi: %s -> xona %s navbatga", topic, number)

await broker.subscribe(EVT_ROOM_VACATED, on_room_vacated)''')
    add_para(
        doc,
        "To'liq hodisa yo'li: (1) /checkout endpointi triggerlaydi → (2) "
        "Reception broker.publish('room.vacated', {...}) chaqiradi → (3) Redis "
        "xabarni room.vacated kanalida nashr etadi → (4) Housekeeping pubsub "
        "loop xabarni qabul qilib on_room_vacated() handlerini chaqiradi → "
        "(5) handler xonani tozalash navbatiga (deque) qo'shadi.",
    )

    add_heading(doc, "2-misol: WebSocket orqali jonli yangilanish", level=3)
    add_para(
        doc,
        "Dashboard servisi /ws WebSocket endpointini taqdim etadi. Brauzer "
        "panel ulanganda, ConnectionManager mijozni faol ulanishlar ro'yxatiga "
        "qo'shadi va dastlabki holatni yuboradi. So'ngra Dashboard har qanday "
        "broker hodisasini qabul qilganda, uni barcha ulangan mijozlarga "
        "uzatadi.",
    )
    add_code(doc, '''# Dashboard hodisa qabul qiladi va WebSocket orqali tarqatadi:
async def on_room_cleaned(topic, payload):
    state.update_room(int(payload["room_number"]), status="clean")
    await manager.broadcast({"type": "room.cleaned", "payload": payload})

# Brauzer tarafdagi handler (static/app.js):
const wsMsgHandlers = {
  "room.cleaned": (p) => { mergeRoom(p.room_number, "clean"); renderAll(); },
  ...
};''')
    add_para(
        doc,
        "Bu yerda hodisa yo'li yanada uzunroq: foydalanuvchi /mark_clean ni "
        "bosadi → Housekeeping room.cleaned ni nashr etadi → Dashboard "
        "subscribe handler chaqiriladi → ichki state yangilanadi → "
        "ConnectionManager.broadcast() barcha ulangan brauzerlarga JSON "
        "uzatadi → har bir brauzer wsMsgHandlers'da mos handlerni chaqiradi "
        "va DOM yangilanadi. Foydalanuvchi sahifani yangilash kerak emas.",
    )

    add_heading(doc, "2.5 Foydalanilgan Asosiy IDE Komponentlari", level=2)
    add_para(
        doc,
        "Loyiha Visual Studio Code muharririda yozildi. Quyidagi komponentlar "
        "ishlab chiqishni tezlashtirdi va xato tushishini kamaytirdi.",
    )
    add_para(
        doc,
        "Kod muharriri sintaksis ajratib ko'rsatish, avtomatik to'ldirish va "
        "kod yig'ishni taqdim etdi. Pylance kengaytmasi import xatolarini, "
        "tip nomuvofiqliklarini va ishlatilmagan o'zgaruvchilarni daxshatda "
        "ko'rsatdi — bu ishlab chiqish davomida o'nlab xatolarni ushlab "
        "qoldi.",
    )
    add_para(
        doc,
        "Disk raskadrovka vositasi (VS Code'ning ichki Python debugger'i) "
        "to'xtash nuqtalari (F9), kuzatuv ifodalari va chaqiriq stekini "
        "tekshirishni qo'llab-quvvatladi. Birinchi race condition xatosi "
        "(qarang: 4.2-bo'lim) shu vosita yordamida tezda tanazzulga "
        "uchradi.",
    )
    add_para(
        doc,
        "Integratsiya qilingan terminal har bir mikroservisni alohida tabda "
        "ishga tushirishga imkon berdi (uvicorn reception_service.main:app "
        "--reload). Loglar darhol ko'rinardi va broker bilan integratsiya "
        "muammolarini izolyatsiya qilish oson edi.",
    )
    add_para(
        doc,
        "Versiya nazoratini integratsiya (Source Control panel) git commit, "
        "diff va branch boshqarishni grafik interfeys orqali soddalashtirdi. "
        "Har bir o'zgarish vizual diff sifatida ko'rindi — bu refactoring "
        "paytida kutilmagan o'zgarishlarni topishga yordam berdi.",
    )
    add_para(
        doc,
        "O'rnatilgan kengaytmalar: Pylance (tip tekshiruvi), Black Formatter "
        "(avtomatik formatlash, line-length 100), Ruff (linting va isort), "
        "REST Client (HTTP endpointlarni test qilish uchun .http fayllar), "
        "GitLens (commit annotatsiyalari).",
    )
