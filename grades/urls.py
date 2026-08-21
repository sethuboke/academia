from django.urls import path

from . import views

app_name = "grades"

urlpatterns = [
    path(
        "classe-matiere/<int:classe_matiere_pk>/semestre/<int:semestre_pk>/interrogations/saisir/",
        views.SaisieInterrogationView.as_view(),
        name="saisie_interrogation",
    ),
    path(
        "classe-matiere/<int:classe_matiere_pk>/semestre/<int:semestre_pk>/devoir/<int:numero>/saisir/",
        views.SaisieDevoirView.as_view(),
        name="saisie_devoir",
    ),
    path(
        "classe-matiere/<int:classe_matiere_pk>/semestre/<int:semestre_pk>/valider/",
        views.ValiderNotesView.as_view(),
        name="valider_notes",
    ),
    path(
        "classe-matiere/<int:classe_matiere_pk>/semestre/<int:semestre_pk>/releve/",
        views.ReleveNotesView.as_view(),
        name="releve_notes",
    ),
]