from django import forms
from django.shortcuts import get_object_or_404, render
from django.views import View

from academics.models import Classe, Eleve
from grades.views import construire_bilan_eleve


class IdentificationEleveForm(forms.Form):
    """Formulaire public : nom + prénom pour retrouver l'élève dans la classe du lien."""
    nom = forms.CharField(max_length=100, label="Nom", widget=forms.TextInput(attrs={
        "placeholder": "Votre nom", "class": "w-full px-4 py-3 rounded-xl border border-blue-bell-200 bg-white text-blue-bell-900 placeholder-blue-bell-400 focus:outline-none focus:ring-2 focus:ring-blue-bell-500 focus:border-transparent transition",
    }))
    prenom = forms.CharField(max_length=100, label="Prénom", widget=forms.TextInput(attrs={
        "placeholder": "Votre prénom", "class": "w-full px-4 py-3 rounded-xl border border-blue-bell-200 bg-white text-blue-bell-900 placeholder-blue-bell-400 focus:outline-none focus:ring-2 focus:ring-blue-bell-500 focus:border-transparent transition",
    }))


class ConsultationEleveView(View):
    """
    Vue publique (§5.4) : un élève accède à ses notes via le lien court
    propre à sa classe et s'identifie par nom + prénom.
    Seules les notes validées (valide=True) sont affichées.
    """

    def get(self, request, lien_uid):
        classe = get_object_or_404(Classe, lien_public_uid=lien_uid)
        return render(request, "grades/bilan_eleve.html", {
            "classe": classe,
            "form": IdentificationEleveForm(),
            "public_mode": True,
        })

    def post(self, request, lien_uid):
        classe = get_object_or_404(Classe, lien_public_uid=lien_uid)
        form = IdentificationEleveForm(request.POST)
        if not form.is_valid():
            return render(request, "grades/bilan_eleve.html", {
                "classe": classe,
                "form": form,
                "public_mode": True,
            })

        eleve = Eleve.objects.filter(
            classe=classe,
            nom__iexact=form.cleaned_data["nom"].strip(),
            prenom__iexact=form.cleaned_data["prenom"].strip(),
        ).first()

        contexte = {
            "classe": classe,
            "form": form,
            "eleve": eleve,
            "public_mode": True,
        }
        if eleve:
            contexte.update(construire_bilan_eleve(eleve, seulement_validees=True))
        else:
            contexte["identification_invalide"] = True
        return render(request, "grades/bilan_eleve.html", contexte)