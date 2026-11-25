from django import forms

from .models import Application
from .validators import normalize_passport_number, normalize_phone_number

TEXT_INPUT_CLASS = (
    "w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 "
    "placeholder-slate-400 shadow-xs transition focus:border-blue-600 focus:outline-none "
    "focus:ring-4 focus:ring-blue-100"
)


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = [
            "full_name",
            "phone_number",
            "passport_number",
            "passport_file",
        ]
        labels = {
            "full_name": "Ism familiya sharifi",
            "phone_number": "Telefon raqami",
            "passport_number": "Passport seriyasi va raqami",
            "passport_file": "Passport nusxasi (PDF)",
        }
        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": TEXT_INPUT_CLASS,
                    "placeholder": "Masalan: Alisherov Jasur Karimovich",
                    "autocomplete": "name",
                    "required": True,
                }
            ),
            "phone_number": forms.TextInput(
                attrs={
                    "class": TEXT_INPUT_CLASS,
                    "placeholder": "+998 90 123 45 67",
                    "autocomplete": "tel",
                    "inputmode": "tel",
                    "required": True,
                }
            ),
            "passport_number": forms.TextInput(
                attrs={
                    "class": f"{TEXT_INPUT_CLASS} uppercase tracking-wider",
                    "placeholder": "AA1234567",
                    "maxlength": "12",
                    "autocomplete": "off",
                    "required": True,
                }
            ),
            "passport_file": forms.ClearableFileInput(
                attrs={
                    "class": "sr-only",
                    "accept": ".pdf,application/pdf",
                    "required": True,
                }
            ),
        }
        error_messages = {
            "full_name": {
                "required": "Ism familiya sharifini kiritish majburiy.",
                "max_length": "Ism familiya sharifi juda uzun.",
            },
            "phone_number": {
                "required": "Telefon raqamini kiritish majburiy.",
                "max_length": "Telefon raqami juda uzun.",
            },
            "passport_number": {
                "required": "Passport seriyasi va raqamini kiritish majburiy.",
                "max_length": "Passport seriyasi va raqami juda uzun.",
            },
            "passport_file": {
                "required": "Passport nusxasi (PDF) faylini yuklash majburiy.",
            },
        }

    def clean_full_name(self) -> str:
        return " ".join(self.cleaned_data["full_name"].strip().split())

    def clean_phone_number(self) -> str:
        return normalize_phone_number(self.cleaned_data["phone_number"])

    def clean_passport_number(self) -> str:
        return normalize_passport_number(self.cleaned_data["passport_number"])


class TrackingForm(forms.Form):
    tracking_code = forms.CharField(
        label="Ariza raqami",
        max_length=20,
        required=True,
        error_messages={
            "required": "Iltimos, ariza raqamini kiriting.",
            "max_length": "Ariza raqami noto'g'ri formatda.",
        },
        widget=forms.TextInput(
            attrs={
                "class": f"{TEXT_INPUT_CLASS} uppercase font-mono tracking-wider",
                "placeholder": "Masalan: AL-2026-A8K92F",
                "autocomplete": "off",
                "required": True,
            }
        ),
    )

    def clean_tracking_code(self) -> str:
        return self.cleaned_data["tracking_code"].strip().upper()
