from django.urls import path

from . import views

app_name = "sanctions"

urlpatterns = [
    path("classes/<int:classe_pk>/sanctions/", views.SanctionListCreateView.as_view(), name="sanction_list"),
    path("sanctions/<int:pk>/supprimer/", views.SanctionDeleteView.as_view(), name="sanction_delete"),
]