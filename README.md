# Elektron Ariza Tizimi (Online Application Submission & Tracking MVP)

A clean, secure Django MVP web application allowing citizens to submit online applications with a PDF copy of their passport, receive a unique cryptographically generated tracking code, and check their application status publicly without exposing personal data. Administrators manage applications, update statuses, and securely download passport PDFs through Django Admin.

## Technology Stack

- **Backend:** Python 3, Django, SQLite
- **Frontend:** HTML5, Tailwind CSS (CDN), Vanilla JavaScript, Django Templates
- **Configuration:** `python-dotenv` (`.env` environment variables)

## Features

- **Public Application Form (`/`)**: Uzbek (Latin) interface with client-side and server-side validation, 5 MB PDF upload limit, PDF magic-byte signature verification, selected filename preview, loading state, duplicate-click prevention, and CSRF protection.
- **Submission Success (`/success/`)**: Displays the generated unique tracking code (e.g., `AL-2026-A8K92F`), copy-to-clipboard button, save reminder, and quick link to check status.
- **Public Application Tracking (`/track/`)**: Displays only the tracking code, submission date, and current status (`Kutilmoqda`, `Ko'rib chiqilmoqda`, `Tasdiqlandi`, `Rad etildi`) — never exposes personal information or files.
- **Protected Admin Panel (`/admin/`)**: Search by tracking code, applicant name, or passport number; filter by status and submission date; update statuses individually or in bulk; download passport PDFs strictly via an authenticated staff-only endpoint from private storage (`private_media/`).

## Installation & Setup (Windows PowerShell)

### 1. Open the project directory

```powershell
cd c:\Users\Alisher\Ariza_webapp
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> If PowerShell blocks script activation, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once, or run commands using `.venv\Scripts\python.exe` directly.

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Generate a strong secret key and place it in `.env`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Example `.env` values:

```ini
DJANGO_SECRET_KEY=<paste-generated-secret-key>
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_TIME_ZONE=Asia/Tashkent
```

### 5. Run database migrations

```powershell
python manage.py makemigrations
python manage.py migrate
```

### 6. Create an administrator (superuser)

```powershell
python manage.py createsuperuser
```

Follow the prompts to set a username, email, and password.

### 7. Start the development server

```powershell
python manage.py runserver
```

## Accessing the Application

- **Application Form (Ariza topshirish):** http://127.0.0.1:8000/
- **Application Tracking (Ariza holatini tekshirish):** http://127.0.0.1:8000/track/
- **Django Admin Panel:** http://127.0.0.1:8000/admin/

## Running Automated Tests

```powershell
python manage.py test
```

## Security Notes

- Uploaded passport PDFs are stored in `private_media/` with randomized UUID filenames and are **never** served via public static or media URLs.
- File uploads validate `.pdf` extension, maximum size (5 MB), `%PDF-` header signature, and `%%EOF` trailer.
- Only authenticated staff users with view permission can download passport PDFs via the protected admin download route.
- Keep `.env` out of version control and set `DJANGO_DEBUG=False` with a strong `DJANGO_SECRET_KEY` in production.
