from django import forms

from .models import AnneeScolaire, Classe, Eleve, ClasseMatiere, Matiere, Semestre

# Classes Tailwind communes pour tous les champs de formulaire
FIELD_CLASSES = "w-full px-4 py-2.5 rounded-xl border border-blue-bell-200 bg-white text-blue-bell-900 placeholder-blue-bell-400 focus:outline-none focus:ring-2 focus:ring-blue-bell-500 focus:border-transparent transition text-sm"
SELECT_CLASSES = FIELD_CLASSES + " appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2024%2024%22%20stroke%3D%22%230f3757%22%20stroke-width%3D%222%22%3E%3Cpath%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20d%3D%22M19%209l-7%207-7-7%22%2F%3E%3C%2Fsvg%3E')] bg-no-repeat bg-[right_0.75rem_center] bg-[length:1rem] pr-10 cursor-pointer"


class AnneeScolaireForm(forms.ModelForm):
    class Meta:
        model = AnneeScolaire
        fields = ["libelle", "est_courante"]
        widgets = {
            "libelle": forms.TextInput(attrs={"class": FIELD_CLASSES, "placeholder": "Ex : 2025-2026"}),
            "est_courante": forms.CheckboxInput(attrs={"class": "w-5 h-5 rounded border-blue-bell-300 text-blue-bell-600 focus:ring-blue-bell-500"}),
        }


class SemestreForm(forms.ModelForm):
    class Meta:
        model = Semestre
        fields = ["annee_scolaire", "libelle"]
        widgets = {
            "annee_scolaire": forms.Select(attrs={"class": SELECT_CLASSES}),
            "libelle": forms.Select(attrs={"class": SELECT_CLASSES}),
        }


class MatiereForm(forms.ModelForm):
    class Meta:
        model = Matiere
        fields = ["nom"]
        widgets = {
            "nom": forms.TextInput(attrs={"class": FIELD_CLASSES, "placeholder": "Ex : Mathématiques"}),
        }


class ClasseForm(forms.ModelForm):
    class Meta:
        model = Classe
        fields = ["annee_scolaire", "nom"]
        widgets = {
            "annee_scolaire": forms.Select(attrs={"class": SELECT_CLASSES}),
            "nom": forms.TextInput(attrs={"class": FIELD_CLASSES, "placeholder": "Ex : Terminale D"}),
        }


class EleveForm(forms.ModelForm):
    class Meta:
        model = Eleve
        fields = ["nom", "prenom"]
        widgets = {
            "nom": forms.TextInput(attrs={"class": FIELD_CLASSES, "placeholder": "Nom de famille"}),
            "prenom": forms.TextInput(attrs={"class": FIELD_CLASSES, "placeholder": "Prénom"}),
        }


class ClasseMatiereForm(forms.ModelForm):
    class Meta:
        model = ClasseMatiere
        fields = ["matiere", "coefficient"]
        widgets = {
            "matiere": forms.Select(attrs={"class": SELECT_CLASSES}),
            "coefficient": forms.NumberInput(attrs={
                "class": FIELD_CLASSES,
                "min": 1,
                "placeholder": "Ex : 2",
            }),
        }