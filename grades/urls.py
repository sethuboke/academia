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
        "classe/<int:classe_pk>/semestre/<int:semestre_pk>/conduite/saisir/",
        views.SaisieConduiteView.as_view(),
        name="saisie_conduite",
    ),
    path(
        "classe/<int:classe_pk>/semestre/<int:semestre_pk>/conduite/valider/",
        views.ValiderConduitesView.as_view(),
        name="valider_conduites",
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
    path(
        "eleves/<int:pk>/bilan/",
        views.BilanEleveView.as_view(),
        name="bilan_eleve",
    ),
    path(
        "classes/<int:pk>/bilan/",
        views.ClasseBilanView.as_view(),
        name="bilan_classe",
    ),
    path(
        "classes/<int:pk>/statistique/",
        views.ClasseStatistiqueView.as_view(),
        name="statistique_classe",
    ),
    path(
        "classes/<int:pk>/bilan/semestre/<int:semestre_pk>/pdf/",
        views.ClasseBilanPdfView.as_view(),
        name="bilan_classe_pdf",
    ),
]