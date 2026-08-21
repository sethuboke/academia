from django.urls import path

from . import views

app_name = "student_access"

urlpatterns = [
    path(
        "eleve/<uuid:lien_uid>/",
        views.ConsultationEleveView.as_view(),
        name="consulter",
    ),
]