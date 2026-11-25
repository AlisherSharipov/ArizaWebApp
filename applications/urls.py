from django.urls import path

from . import views

app_name = "applications"

urlpatterns = [
    path("", views.application_create, name="home"),
    path("success/", views.application_success, name="success"),
    path("track/", views.application_track, name="track"),
]
