from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import ApplicationForm, TrackingForm
from .models import Application


@require_http_methods(["GET", "POST"])
def application_create(request):
    if request.method == "POST":
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save()
            request.session["last_tracking_code"] = application.tracking_code
            messages.success(
                request,
                "Arizangiz muvaffaqiyatli yuborildi. Ariza raqamingizni saqlab qo'ying.",
            )
            return redirect("applications:success")
    else:
        form = ApplicationForm()

    return render(
        request,
        "applications/home.html",
        {
            "form": form,
            "active_nav": "home",
        },
    )


@require_http_methods(["GET"])
def application_success(request):
    tracking_code = request.session.get("last_tracking_code")
    if not tracking_code:
        messages.info(request, "Yangi ariza topshirish uchun quyidagi shaklni to'ldiring.")
        return redirect("applications:home")

    return render(
        request,
        "applications/success.html",
        {
            "tracking_code": tracking_code,
            "active_nav": "home",
        },
    )


@require_http_methods(["GET", "POST"])
def application_track(request):
    tracking_result = None
    not_found = False

    if request.method == "POST":
        form = TrackingForm(request.POST)
    elif "code" in request.GET and request.GET.get("code", "").strip():
        form = TrackingForm({"tracking_code": request.GET.get("code", "")})
    else:
        form = TrackingForm()

    if form.is_bound and form.is_valid():
        code = form.cleaned_data["tracking_code"]
        # Query and expose ONLY non-personal tracking metadata
        application = (
            Application.objects.only("tracking_code", "status", "created_at")
            .filter(tracking_code=code)
            .first()
        )
        if application:
            tracking_result = {
                "tracking_code": application.tracking_code,
                "status": application.status,
                "status_display": application.get_status_display(),
                "created_at": application.created_at,
            }
        else:
            not_found = True

    return render(
        request,
        "applications/tracking.html",
        {
            "form": form,
            "tracking_result": tracking_result,
            "not_found": not_found,
            "active_nav": "track",
        },
    )
