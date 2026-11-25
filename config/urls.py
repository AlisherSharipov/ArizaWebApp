from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Ariza Tizimi — Boshqaruv Paneli"
admin.site.site_title = "Ariza Admin"
admin.site.index_title = "Arizalarni boshqarish"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("applications.urls")),
]
