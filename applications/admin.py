from pathlib import Path

from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html

from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "tracking_code",
        "full_name",
        "phone_number",
        "passport_number",
        "status_badge",
        "created_at",
        "passport_download_link",
    )
    list_filter = ("status", "created_at")
    search_fields = ("tracking_code", "full_name", "passport_number")
    readonly_fields = (
        "tracking_code",
        "created_at",
        "updated_at",
        "passport_download_link",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    actions = (
        "mark_as_pending",
        "mark_as_under_review",
        "mark_as_approved",
        "mark_as_rejected",
    )

    def get_fields(self, request, obj=None):
        if obj is None:
            return (
                "full_name",
                "phone_number",
                "passport_number",
                "passport_file",
                "status",
            )
        return (
            "tracking_code",
            "full_name",
            "phone_number",
            "passport_number",
            "passport_download_link",
            "status",
            "created_at",
            "updated_at",
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/download-passport/",
                self.admin_site.admin_view(self.download_passport_view),
                name="applications_application_download_passport",
            ),
        ]
        return custom_urls + urls

    @admin.display(description="Ariza holati", ordering="status")
    def status_badge(self, obj: Application):
        styles = {
            Application.Status.PENDING: "background:#FEF3C7;color:#92400E;",
            Application.Status.UNDER_REVIEW: "background:#DBEAFE;color:#1E40AF;",
            Application.Status.APPROVED: "background:#DCFCE7;color:#166534;",
            Application.Status.REJECTED: "background:#FEE2E2;color:#991B1B;",
        }
        style = styles.get(obj.status, "background:#E2E8F0;color:#334155;")
        return format_html(
            '<span style="display:inline-block;padding:3px 10px;border-radius:9999px;font-weight:600;font-size:12px;{}">{}</span>',
            style,
            obj.get_status_display(),
        )

    @admin.display(description="Passport nusxasi (PDF)")
    def passport_download_link(self, obj: Application):
        if not obj or not obj.pk or not obj.passport_file:
            return "Fayl mavjud emas"
        url = reverse("admin:applications_application_download_passport", args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" style="white-space:nowrap;">PDF yuklab olish</a>',
            url,
        )

    def download_passport_view(self, request, object_id: int):
        """Serve the applicant's passport PDF strictly to authenticated staff with view permission."""
        if not (request.user.is_active and request.user.is_staff):
            raise PermissionDenied

        application = get_object_or_404(Application, pk=object_id)
        if not self.has_view_permission(request, application):
            raise PermissionDenied

        if not application.passport_file:
            raise Http404("Passport fayli topilmadi.")

        private_root = Path(settings.PRIVATE_MEDIA_ROOT).resolve()
        file_path = Path(application.passport_file.path).resolve()

        # Defense-in-depth against path traversal outside PRIVATE_MEDIA_ROOT
        if private_root not in file_path.parents or not file_path.is_file():
            raise Http404("Passport fayli topilmadi.")

        download_name = f"{application.tracking_code}_passport.pdf"
        response = FileResponse(
            file_path.open("rb"),
            as_attachment=True,
            filename=download_name,
            content_type="application/pdf",
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "no-store, private"
        return response

    @admin.action(description="Holatni 'Kutilmoqda' ga o'zgartirish")
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(status=Application.Status.PENDING)
        self.message_user(request, f"{updated} ta ariza holati 'Kutilmoqda' ga o'zgartirildi.", messages.SUCCESS)

    @admin.action(description="Holatni 'Ko'rib chiqilmoqda' ga o'zgartirish")
    def mark_as_under_review(self, request, queryset):
        updated = queryset.update(status=Application.Status.UNDER_REVIEW)
        self.message_user(request, f"{updated} ta ariza holati 'Ko'rib chiqilmoqda' ga o'zgartirildi.", messages.SUCCESS)

    @admin.action(description="Holatni 'Tasdiqlandi' ga o'zgartirish")
    def mark_as_approved(self, request, queryset):
        updated = queryset.update(status=Application.Status.APPROVED)
        self.message_user(request, f"{updated} ta ariza holati 'Tasdiqlandi' ga o'zgartirildi.", messages.SUCCESS)

    @admin.action(description="Holatni 'Rad etildi' ga o'zgartirish")
    def mark_as_rejected(self, request, queryset):
        updated = queryset.update(status=Application.Status.REJECTED)
        self.message_user(request, f"{updated} ta ariza holati 'Rad etildi' ga o'zgartirildi.", messages.SUCCESS)
