import re
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Application

SAMPLE_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    b"2 0 obj << /Type /Pages /Kids [] /Count 0 >> endobj\n"
    b"trailer << /Root 1 0 R >>\n"
    b"%%EOF\n"
)


class ApplicationSystemTests(TestCase):
    def setUp(self):
        cache.clear()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.private_media_override = override_settings(
            PRIVATE_MEDIA_ROOT=Path(self.temp_dir.name)
        )
        self.private_media_override.enable()

    def tearDown(self):
        self.private_media_override.disable()
        self.temp_dir.cleanup()
        cache.clear()

    def _make_pdf(self, name="passport.pdf", content=SAMPLE_PDF_BYTES):
        return SimpleUploadedFile(name, content, content_type="application/pdf")

    def _valid_post_data(self, pdf_file=None):
        return {
            "full_name": "Alisherov Jasur Karimovich",
            "phone_number": "+998 90 123 45 67",
            "passport_number": "aa 1234567",
            "passport_file": pdf_file or self._make_pdf(),
        }

    def test_home_page_renders_uzbek_labels(self):
        response = self.client.get(reverse("applications:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ariza topshirish")
        self.assertContains(response, "Ism familiya sharifi")
        self.assertContains(response, "Telefon raqami")
        self.assertContains(response, "Passport seriyasi va raqami")
        self.assertContains(response, "Passport nusxasi (PDF)")
        self.assertContains(response, "Arizani yuborish")
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_submit_valid_application_and_success_page(self):
        response = self.client.post(
            reverse("applications:home"),
            data=self._valid_post_data(self._make_pdf(name="../../evil.pdf")),
        )
        self.assertRedirects(response, reverse("applications:success"))

        self.assertEqual(Application.objects.count(), 1)
        app = Application.objects.first()
        self.assertRegex(app.tracking_code, r"^AL-\d{4}-[A-Z0-9]{6}$")
        self.assertEqual(app.phone_number, "+998901234567")
        self.assertEqual(app.passport_number, "AA1234567")
        self.assertEqual(app.status, Application.Status.PENDING)
        # Ensure original dangerous filename is not used
        self.assertNotIn("evil", app.passport_file.name)
        self.assertNotIn("..", app.passport_file.name)
        self.assertTrue(Path(app.passport_file.path).is_file())

        success_response = self.client.get(reverse("applications:success"))
        self.assertEqual(success_response.status_code, 200)
        self.assertContains(success_response, app.tracking_code)
        self.assertContains(success_response, "Ariza holatini tekshirish")

    def test_reject_non_pdf_extension(self):
        bad_file = SimpleUploadedFile(
            "passport.txt", SAMPLE_PDF_BYTES, content_type="text/plain"
        )
        response = self.client.post(
            reverse("applications:home"),
            data=self._valid_post_data(pdf_file=bad_file),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Application.objects.count(), 0)
        self.assertContains(response, "Faqat PDF formatidagi")

    def test_reject_spoofed_pdf_signature(self):
        spoofed = SimpleUploadedFile(
            "fake.pdf", b"not actually a pdf file", content_type="application/pdf"
        )
        response = self.client.post(
            reverse("applications:home"),
            data=self._valid_post_data(pdf_file=spoofed),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Application.objects.count(), 0)
        self.assertContains(response, "haqiqiy PDF hujjat emas")

    def test_reject_oversized_pdf(self):
        oversized_bytes = b"%PDF-1.4\n" + (b"0" * (5 * 1024 * 1024 + 100)) + b"\n%%EOF"
        big_pdf = SimpleUploadedFile(
            "large.pdf", oversized_bytes, content_type="application/pdf"
        )
        response = self.client.post(
            reverse("applications:home"),
            data=self._valid_post_data(pdf_file=big_pdf),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Application.objects.count(), 0)
        self.assertContains(response, "5 MB dan oshmasligi kerak")

    def test_tracking_hides_personal_information(self):
        app = Application.objects.create(
            full_name="Karimova Dilnoza Rustamovna",
            phone_number="+998911112233",
            passport_number="AB7654321",
            passport_file=self._make_pdf(),
            status=Application.Status.UNDER_REVIEW,
        )

        response = self.client.post(
            reverse("applications:track"),
            data={"tracking_code": app.tracking_code.lower()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, app.tracking_code)
        self.assertContains(response, "Ko&#x27;rib chiqilmoqda")
        self.assertContains(response, "Yuborilgan sana")

        # Sensitive PII must NEVER appear on public tracking page
        self.assertNotContains(response, "Karimova")
        self.assertNotContains(response, "Dilnoza")
        self.assertNotContains(response, "+998911112233")
        self.assertNotContains(response, "AB7654321")
        self.assertNotContains(response, app.passport_file.name)

    def test_tracking_nonexistent_code_shows_friendly_error(self):
        response = self.client.post(
            reverse("applications:track"),
            data={"tracking_code": "AL-2026-ZZZZZZ"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ariza topilmadi")

    def test_private_media_is_not_publicly_exposed(self):
        app = Application.objects.create(
            full_name="Valiyev Sardorbek Olimovich",
            phone_number="+998901234567",
            passport_number="AD1112233",
            passport_file=self._make_pdf(),
        )
        response = self.client.get(f"/private_media/{app.passport_file.name}")
        self.assertEqual(response.status_code, 404)
        response_media = self.client.get(f"/media/{app.passport_file.name}")
        self.assertEqual(response_media.status_code, 404)

    def test_admin_protected_passport_download(self):
        app = Application.objects.create(
            full_name="Toshmatov Bobur Akmalovich",
            phone_number="+998935556677",
            passport_number="AC9876543",
            passport_file=self._make_pdf(),
        )
        download_url = reverse(
            "admin:applications_application_download_passport", args=[app.pk]
        )

        # Anonymous user is redirected to admin login
        anon_resp = self.client.get(download_url)
        self.assertEqual(anon_resp.status_code, 302)
        self.assertIn("/admin/login/", anon_resp["Location"])

        # Authenticated regular (non-staff) user cannot download
        User = get_user_model()
        regular_user = User.objects.create_user(
            username="citizen", password="StrongPassword123!"
        )
        self.client.force_login(regular_user)
        reg_resp = self.client.get(download_url)
        self.assertEqual(reg_resp.status_code, 302)
        self.assertIn("/admin/login/", reg_resp["Location"])

        # Authenticated superuser can download with secure headers
        admin_user = User.objects.create_superuser(
            username="admin_test",
            email="admin@example.com",
            password="StrongAdminPassword123!",
        )
        self.client.force_login(admin_user)
        admin_resp = self.client.get(download_url)
        self.assertEqual(admin_resp.status_code, 200)
        self.assertEqual(admin_resp["Content-Type"], "application/pdf")
        self.assertEqual(admin_resp["X-Content-Type-Options"], "nosniff")
        self.assertIn(
            f"{app.tracking_code}_passport.pdf", admin_resp["Content-Disposition"]
        )
        downloaded_bytes = b"".join(admin_resp.streaming_content)
        self.assertEqual(downloaded_bytes, SAMPLE_PDF_BYTES)

    def test_admin_list_search_filter_and_status_update(self):
        app = Application.objects.create(
            full_name="Mirzayev Akmal Rustamovich",
            phone_number="+998971234567",
            passport_number="AE5554433",
            passport_file=self._make_pdf(),
        )
        User = get_user_model()
        admin_user = User.objects.create_superuser(
            username="admin_manage",
            email="manage@example.com",
            password="StrongAdminPassword123!",
        )
        self.client.force_login(admin_user)

        changelist_url = reverse("admin:applications_application_changelist")
        list_resp = self.client.get(changelist_url, {"q": app.tracking_code})
        self.assertEqual(list_resp.status_code, 200)
        self.assertContains(list_resp, app.tracking_code)
        self.assertContains(list_resp, "PDF yuklab olish")

        change_url = reverse("admin:applications_application_change", args=[app.pk])
        detail_resp = self.client.get(change_url)
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, app.tracking_code)

        update_resp = self.client.post(
            change_url,
            data={
                "full_name": app.full_name,
                "phone_number": app.phone_number,
                "passport_number": app.passport_number,
                "status": Application.Status.APPROVED,
            },
            follow=True,
        )
        self.assertEqual(update_resp.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, Application.Status.APPROVED)

        # Public tracking page (as anonymous citizen) reflects updated status without PII
        self.client.logout()
        track_resp = self.client.get(
            reverse("applications:track"), {"code": app.tracking_code}
        )
        self.assertEqual(track_resp.status_code, 200)
        self.assertContains(track_resp, "Tasdiqlandi")
        self.assertNotContains(track_resp, "Mirzayev")

    def test_admin_login_rate_limiting(self):
        login_url = reverse("admin:login")
        for _ in range(5):
            resp = self.client.post(
                login_url,
                data={"username": "nonexistent", "password": "wrongpassword"},
            )
            self.assertEqual(resp.status_code, 200)

        blocked_resp = self.client.post(
            login_url,
            data={"username": "nonexistent", "password": "wrongpassword"},
        )
        self.assertEqual(blocked_resp.status_code, 429)
