import os
import secrets
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import IntegrityError, models
from django.utils import timezone
from django.utils.deconstruct import deconstructible

from .validators import (
    normalize_passport_number,
    normalize_phone_number,
    validate_full_name,
    validate_passport_number,
    validate_passport_pdf,
    validate_phone_number,
)

# Unambiguous uppercase alphanumeric characters for readable tracking codes
TRACKING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


@deconstructible
class PrivatePassportStorage(FileSystemStorage):
    """Stores passport PDFs in PRIVATE_MEDIA_ROOT and blocks public URL generation."""

    def __init__(self):
        super().__init__(base_url=None)

    @property
    def base_location(self) -> str:
        return str(settings.PRIVATE_MEDIA_ROOT)

    @property
    def location(self) -> str:
        return os.path.abspath(self.base_location)

    def url(self, name: str) -> str:
        raise ValueError("Passport files are private and not accessible via public URLs.")


private_passport_storage = PrivatePassportStorage()


def passport_upload_path(instance, filename: str) -> str:
    """Generate a safe, non-guessable path in private storage to prevent traversal and collisions."""
    now = timezone.now()
    return f"passports/{now:%Y}/{now:%m}/{uuid.uuid4().hex}.pdf"


def generate_tracking_code() -> str:
    """Generate a cryptographically secure tracking code such as AL-2026-A8K92F."""
    year = timezone.now().year
    token = "".join(secrets.choice(TRACKING_ALPHABET) for _ in range(6))
    return f"AL-{year}-{token}"


class Application(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        UNDER_REVIEW = "under_review", "Ko'rib chiqilmoqda"
        APPROVED = "approved", "Tasdiqlandi"
        REJECTED = "rejected", "Rad etildi"

    tracking_code = models.CharField(
        "Ariza raqami",
        max_length=20,
        unique=True,
        db_index=True,
        editable=False,
    )
    full_name = models.CharField(
        "Ism familiya sharifi",
        max_length=150,
        validators=[validate_full_name],
    )
    phone_number = models.CharField(
        "Telefon raqami",
        max_length=20,
        validators=[validate_phone_number],
    )
    passport_number = models.CharField(
        "Passport seriyasi va raqami",
        max_length=20,
        validators=[validate_passport_number],
    )
    passport_file = models.FileField(
        "Passport nusxasi (PDF)",
        storage=private_passport_storage,
        upload_to=passport_upload_path,
        validators=[validate_passport_pdf],
    )
    status = models.CharField(
        "Ariza holati",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(
        "Yuborilgan sana",
        auto_now_add=True,
        db_index=True,
    )
    updated_at = models.DateTimeField(
        "Yangilangan sana",
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Ariza"
        verbose_name_plural = "Arizalar"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "pending",
                        "under_review",
                        "approved",
                        "rejected",
                    ]
                ),
                name="application_status_valid",
            )
        ]

    def __str__(self) -> str:
        return f"{self.tracking_code} — {self.full_name}"

    def _assign_unique_tracking_code(self) -> None:
        for _ in range(10):
            candidate = generate_tracking_code()
            if not Application.objects.filter(tracking_code=candidate).exists():
                self.tracking_code = candidate
                return
        raise RuntimeError("Unikal ariza raqamini yaratib bo'lmadi.")

    def save(self, *args, **kwargs):
        self.full_name = " ".join(self.full_name.strip().split())
        self.phone_number = normalize_phone_number(self.phone_number)
        self.passport_number = normalize_passport_number(self.passport_number)

        if self.tracking_code:
            return super().save(*args, **kwargs)

        # Retry on rare race-condition collision for tracking_code uniqueness
        for attempt in range(5):
            self._assign_unique_tracking_code()
            try:
                return super().save(*args, **kwargs)
            except IntegrityError:
                if attempt == 4:
                    raise
                self.tracking_code = ""
