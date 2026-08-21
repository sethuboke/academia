from django.urls import path

from . import views

app_name = "attendance"

urlpatterns = [
    path("classes/<int:classe_pk>/absences/", views.AbsenceListCreateView.as_view(), name="absence_list"),
    path("absences/<int:pk>/supprimer/", views.AbsenceDeleteView.as_view(), name="absence_delete"),
]