from django.urls import path

from . import views

app_name = "academics"

urlpatterns = [
    # Années scolaires
    path("annees-scolaires/", views.AnneeScolaireListView.as_view(), name="anneescolaire_list"),
    path("annees-scolaires/ajouter/", views.AnneeScolaireCreateView.as_view(), name="anneescolaire_create"),
    path("annees-scolaires/<int:pk>/modifier/", views.AnneeScolaireUpdateView.as_view(), name="anneescolaire_update"),
    path("annees-scolaires/<int:pk>/supprimer/", views.AnneeScolaireDeleteView.as_view(), name="anneescolaire_delete"),

    # Semestres
    path("semestres/", views.SemestreListView.as_view(), name="semestre_list"),
    path("semestres/ajouter/", views.SemestreCreateView.as_view(), name="semestre_create"),
    path("semestres/<int:pk>/modifier/", views.SemestreUpdateView.as_view(), name="semestre_update"),
    path("semestres/<int:pk>/supprimer/", views.SemestreDeleteView.as_view(), name="semestre_delete"),

    # Matières
    path("matieres/", views.MatiereListView.as_view(), name="matiere_list"),
    path("matieres/ajouter/", views.MatiereCreateView.as_view(), name="matiere_create"),
    path("matieres/<int:pk>/modifier/", views.MatiereUpdateView.as_view(), name="matiere_update"),
    path("matieres/<int:pk>/supprimer/", views.MatiereDeleteView.as_view(), name="matiere_delete"),

    # Classes
    path("classes/", views.ClasseListView.as_view(), name="classe_list"),
    path("classes/ajouter/", views.ClasseCreateView.as_view(), name="classe_create"),
    path("classes/<int:pk>/", views.ClasseDetailView.as_view(), name="classe_detail"),
    path("classes/<int:pk>/modifier/", views.ClasseUpdateView.as_view(), name="classe_update"),
    path("classes/<int:pk>/supprimer/", views.ClasseDeleteView.as_view(), name="classe_delete"),

    path("classes/<int:classe_pk>/eleves/ajouter/", views.EleveCreateView.as_view(), name="eleve_create"),
    path("eleves/<int:pk>/modifier/", views.EleveUpdateView.as_view(), name="eleve_update"),
    path("eleves/<int:pk>/supprimer/", views.EleveDeleteView.as_view(), name="eleve_delete"),

    path(
        "classes/<int:classe_pk>/matieres/ajouter/",
        views.ClasseMatiereCreateView.as_view(),
        name="classematiere_create",
    ),
]