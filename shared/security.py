"""
HotelOS xavfsizlik moduli.

Uchta asosiy mas'uliyatni qoplaydi:
1. Kiritishni tekshirish (input validation) — har qanday tashqi ma'lumot tekshirilishi kerak.
2. Autentifikatsiya — operatsiyalar paneli uchun JWT tokenlar.
3. Ma'lumotlarni oshkor qilish nazorati — chiqishni filtrlash.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("hotelos.security")

# Validation cheklovlari — sehrli raqamlar emas, nomlangan konstantalar.
MAX_NAME_LENGTH = 100
MIN_NAME_LENGTH = 2
MAX_ROOM_NUMBER = 699
MIN_ROOM_NUMBER = 100
MAX_ORDER_ITEMS = 20
MAX_DESCRIPTION_LENGTH = 500
SENSITIVE_FIELDS = frozenset({"document_id", "payment_card_last4", "password", "jwt_secret"})


class ValidationError(ValueError):
    """Kirish tekshiruvi muvaffaqiyatsiz bo'lganida ko'tariladi."""


class AuthenticationError(Exception):
    """Autentifikatsiya muvaffaqiyatsiz bo'lganida ko'tariladi."""


class InputValidator:
    """Markazlashtirilgan kiritish tekshiruvchi.

    Har bir servis mehmonlardan kelgan ma'lumotni qayta ishlashdan oldin shu
    yerga yo'naltiriladi. Buni servisga qattiq kod qilish o'rniga umumiy
    sinfga olib chiqish "Don't Repeat Yourself" tamoyiliga muvofiq
    (Hunt va Thomas, 2000).
    """

    _NAME_RE = re.compile(r"^[\w\s\-'.]{2,100}$", re.UNICODE)
    _DOC_RE = re.compile(r"^[A-Za-z0-9]{4,30}$")
    _CARD_RE = re.compile(r"^\d{4}$")

    @classmethod
    def validate_room_number(cls, value: Any) -> int:
        """Xona raqamini tekshiradi va butun songa o'tkazadi."""
        try:
            room = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"Xona raqami butun son bo'lishi kerak: {value!r}") from exc
        if not (MIN_ROOM_NUMBER <= room <= MAX_ROOM_NUMBER):
            raise ValidationError(
                f"Xona raqami {MIN_ROOM_NUMBER}–{MAX_ROOM_NUMBER} oralig'ida bo'lishi kerak"
            )
        return room

    @classmethod
    def validate_name(cls, value: Any) -> str:
        """Mehmon ismi: bo'sh emas, ruxsat etilgan belgilar, uzunlik chegarasi."""
        if not isinstance(value, str):
            raise ValidationError("Ism matn bo'lishi kerak")
        cleaned = " ".join(value.split())
        if not cls._NAME_RE.match(cleaned):
            raise ValidationError(
                f"Ism noto'g'ri formatda — uzunligi {MIN_NAME_LENGTH}–{MAX_NAME_LENGTH} "
                "va faqat harf/bo'shliq/tire bo'lishi mumkin"
            )
        return cleaned

    @classmethod
    def validate_document_id(cls, value: Any) -> str:
        """Pasport/ID raqami formatini tekshiradi."""
        if not isinstance(value, str) or not cls._DOC_RE.match(value):
            raise ValidationError("Hujjat ID — 4–30 alfanumerik belgi")
        return value

    @classmethod
    def validate_card_last4(cls, value: Any) -> str:
        """To'lov kartasining oxirgi 4 raqami."""
        if not isinstance(value, str) or not cls._CARD_RE.match(value):
            raise ValidationError("Karta oxirgi raqamlari — to'liq 4 raqam")
        return value

    @classmethod
    def validate_order_items(cls, items: Any) -> list[dict]:
        """Buyurtma elementlari ro'yxatini tekshiradi."""
        if not isinstance(items, list) or not items:
            raise ValidationError("Buyurtmada kamida bitta element bo'lishi kerak")
        if len(items) > MAX_ORDER_ITEMS:
            raise ValidationError(f"Buyurtma {MAX_ORDER_ITEMS} ta elementdan oshmasligi kerak")
        normalised: list[dict] = []
        for raw in items:
            if not isinstance(raw, dict):
                raise ValidationError("Har bir element lug'at bo'lishi kerak")
            name = raw.get("name")
            qty = raw.get("qty", 1)
            price = raw.get("price")
            if not isinstance(name, str) or not name.strip():
                raise ValidationError("Element nomi bo'sh bo'lmasligi kerak")
            try:
                qty_int = int(qty)
                price_f = float(price)
            except (TypeError, ValueError) as exc:
                raise ValidationError("qty butun son, price raqam bo'lishi kerak") from exc
            if qty_int <= 0 or price_f < 0:
                raise ValidationError("qty > 0 va price >= 0 bo'lishi kerak")
            normalised.append({"name": name.strip(), "qty": qty_int, "price": price_f})
        return normalised

    @classmethod
    def validate_description(cls, value: Any) -> str:
        """Texnik xizmat tavsifi uzunligi va formati."""
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("Tavsif bo'sh bo'lmasligi kerak")
        if len(value) > MAX_DESCRIPTION_LENGTH:
            raise ValidationError(
                f"Tavsif {MAX_DESCRIPTION_LENGTH} belgidan oshmasligi kerak"
            )
        return value.strip()


def redact_sensitive(data: dict) -> dict:
    """Lug'atdan maxfiy maydonlarni olib tashlaydi.

    WebSocket orqali panelga uzatiladigan har qanday yuk shu funksiyadan o'tishi
    kerak. Bu "ma'lumotlarni oshkor qilish" zaifligini oldini oladi.
    """
    return {k: ("***" if k in SENSITIVE_FIELDS else v) for k, v in data.items()}


# === Soddalashtirilgan JWT amalga oshirish ===
# Brief baholash uchun "asosiy autentifikatsiya tekshiruvi" so'raydi.
# Ishlab chiqarishda python-jose yoki PyJWT ishlatish tavsiya etiladi.

class SimpleJWT:
    """HMAC-SHA256 asosida minimal JWT amalga oshirish.

    To'liq RFC 7519 muvofiq emas, lekin BTEC darajasidagi autentifikatsiyani
    namoyish etish uchun yetarli. Ishlab chiqarishda `python-jose` ishlatish
    tavsiya etiladi — kod izohida shuni qayd etamiz.
    """

    def __init__(self, secret: str, expiry_minutes: int = 60) -> None:
        if not secret or len(secret) < 16:
            raise ValueError("JWT secret kamida 16 belgidan iborat bo'lishi kerak")
        self._secret = secret.encode()
        self._expiry = timedelta(minutes=expiry_minutes)

    def encode(self, username: str) -> str:
        """Token hosil qiladi: '<username>.<expiry_iso>.<hmac_hex>'."""
        expiry = (datetime.now(timezone.utc) + self._expiry).isoformat()
        body = f"{username}.{expiry}"
        signature = hmac.new(self._secret, body.encode(), hashlib.sha256).hexdigest()
        return f"{body}.{signature}"

    def decode(self, token: str) -> str:
        """Tokenni tekshirib, foydalanuvchi nomini qaytaradi yoki istisno tashlaydi."""
        try:
            username, expiry_str, signature = token.rsplit(".", 2)
        except ValueError as exc:
            raise AuthenticationError("Token noto'g'ri formatda") from exc

        body = f"{username}.{expiry_str}"
        expected = hmac.new(self._secret, body.encode(), hashlib.sha256).hexdigest()
        # hmac.compare_digest — vaqt hujumlariga qarshi (constant-time comparison)
        if not hmac.compare_digest(expected, signature):
            raise AuthenticationError("Token imzosi noto'g'ri")
        try:
            expiry = datetime.fromisoformat(expiry_str)
        except ValueError as exc:
            raise AuthenticationError("Token muddati noto'g'ri formatda") from exc
        if datetime.now(timezone.utc) > expiry:
            raise AuthenticationError("Token muddati o'tgan")
        return username


def hash_password(password: str) -> str:
    """Parolni xeshlash (BTEC darajasida — demonstratsiya uchun PBKDF2)."""
    salt = b"hotelos-static-salt"  # noqa: S105 — namoyish uchun; ishlab chiqarishda har user uchun random
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return dk.hex()


def verify_password(password: str, hashed: str) -> bool:
    """Parolni xeshga taqqoslaydi."""
    return hmac.compare_digest(hash_password(password), hashed)
