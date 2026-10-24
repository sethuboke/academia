from django.urls import path
from django.urls.converters import register_converter

from . import views


class ShortUUIDConverter:
    regex = r"[A-Za-z0-9_-]{22}"

    def to_python(self, value):
        import base64
        import uuid

        return uuid.UUID(bytes=base64.urlsafe_b64decode(value + "=="))

    def to_url(self, value):
        import base64

        return base64.urlsafe_b64encode(value.bytes).decode("ascii").rstrip("=")


register_converter(ShortUUIDConverter, "shortuuid")

app_name = "student_access"

urlpatterns = [
    path(
        "notes/<shortuuid:lien_uid>/",
        views.ConsultationEleveView.as_view(),
        name="consulter",
    ),
    path(
        "eleve/<uuid:lien_uid>/",
        views.ConsultationEleveView.as_view(),
        name="consulter_legacy",
    ),
]