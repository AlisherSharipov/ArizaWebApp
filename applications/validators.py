import os
import re

from django.conf import settings
from django.core.exceptions import ValidationError

FULL_NAME_REGEX = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿА-Яа-яЁёЎўҚқҒғҲҳ\s'\-`‘’]+$")
PHONE_CLEAN_REGEX = re.compile(r"[\s\-\(\)]+")
PHONE_VALID_REGEX = re.compile(r"^\+?[0-9]{9,15}$")
PASSPORT_REGEX = re.compile(r"^[A-Z]{2}[0-9]{7}$")

ALLOWED_PDF_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/octet-stream",
}


def validate_full_name(value: str) -> None:
    cleaned = " ".join(value.strip().split())
    if len(cleaned) < 5:
        raise ValidationError(
            "Ism familiya sharifi kamida 5 ta belgidan iborat bo'lishi kerak."
        )
    if len(cleaned.split()) < 2:
        raise ValidationError(
            "Iltimos, to'liq ism va familiyangizni kiriting."
        )
    if not FULL_NAME_REGEX.match(cleaned):
        raise ValidationError(
            "Ism familiya sharifi faqat harflar, bo'shliq va tutuq belgisidan iborat bo'lishi kerak."
        )


def normalize_phone_number(value: str) -> str:
    return PHONE_CLEAN_REGEX.sub("", value.strip())


def validate_phone_number(value: str) -> None:
    normalized = normalize_phone_number(value)
    if not PHONE_VALID_REGEX.match(normalized):
        raise ValidationError(
            "Telefon raqamini to'g'ri formatda kiriting (masalan: +998901234567)."
        )


def normalize_passport_number(value: str) -> str:
    return re.sub(r"\s+", "", value.strip()).upper()


def validate_passport_number(value: str) -> None:
    normalized = normalize_passport_number(value)
    if not PASSPORT_REGEX.match(normalized):
        raise ValidationError(
            "Passport seriyasi va raqami 2 ta harf va 7 ta raqamdan iborat bo'lishi kerak (masalan: AA1234567)."
        )


def validate_passport_pdf(uploaded_file) -> None:
    """Validate uploaded passport file extension, size limit (5 MB), and PDF binary signature."""
    if not uploaded_file:
        raise ValidationError("Passport nusxasi (PDF) yuklanishi shart.")

    filename = getattr(uploaded_file, "name", "") or ""
    if "\x00" in filename or ".." in filename:
        raise ValidationError("Fayl nomi xavfsizlik talablariga javob bermaydi.")

    _, ext = os.path.splitext(os.path.basename(filename))
    if ext.lower() != ".pdf":
        raise ValidationError("Faqat PDF formatidagi (.pdf) fayllar qabul qilinadi.")

    max_size = getattr(settings, "MAX_PASSPORT_UPLOAD_SIZE", 5 * 1024 * 1024)
    file_size = getattr(uploaded_file, "size", 0)
    if file_size <= 0:
        raise ValidationError("Yuklangan PDF fayl bo'sh bo'lishi mumkin emas.")
    if file_size > max_size:
        raise ValidationError("Fayl hajmi 5 MB dan oshmasligi kerak.")

    content_type = getattr(uploaded_file, "content_type", None)
    if content_type and content_type.lower() not in ALLOWED_PDF_CONTENT_TYPES:
        raise ValidationError("Faqat haqiqiy PDF fayl yuklash mumkin.")

    # Verify PDF magic header (%PDF-) and trailer marker (%%EOF)
    current_pos = uploaded_file.tell() if hasattr(uploaded_file, "tell") else 0
    try:
        uploaded_file.seek(0)
        header = uploaded_file.read(1024)
        if not header.startswith(b"%PDF-"):
            raise ValidationError(
                "Yuklangan fayl haqiqiy PDF hujjat emas. Iltimos, to'g'ri PDF fayl tanlang."
            )

        tail_offset = max(0, file_size - 2048)
        uploaded_file.seek(tail_offset)
        tail = uploaded_file.read(2048)
        if b"%%EOF" not in tail:
            raise ValidationError(
                "PDF fayl shikastlangan yoki to'liq emas. Iltimos, boshqa PDF fayl yuklang."
            )
    finally:
        uploaded_file.seek(current_pos)
