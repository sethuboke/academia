from decimal import Decimal

from django import forms
from django.shortcuts import get_object_or_404, render
from django.views import View

from academics.models import Classe, Eleve
from grades import aggregations
from grades.models import Conduite


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
    Vue publique (§5.4) : un élève accède à ses notes via le lien UUID
    propre à sa classe et s'identifie par nom + prénom.
    Seules les notes validées (valide=True) sont affichées.
    """

    def get(self, request, lien_uid):
        classe = get_object_or_404(Classe, lien_public_uid=lien_uid)
        return render(request, "student_access/consulter.html", {
            "classe": classe,
            "form": IdentificationEleveForm(),
        })

    def post(self, request, lien_uid):
        classe = get_object_or_404(Classe, lien_public_uid=lien_uid)
        form = IdentificationEleveForm(request.POST)
        if not form.is_valid():
            return render(request, "student_access/consulter.html", {
                "classe": classe,
                "form": form,
            })

        eleve = Eleve.objects.filter(
            classe=classe,
            nom__iexact=form.cleaned_data["nom"].strip(),
            prenom__iexact=form.cleaned_data["prenom"].strip(),
        ).first()

        return render(request, "student_access/consulter.html", {
            "classe": classe,
            "form": form,
            "eleve": eleve,
            "moyennes": self._build_moyennes(eleve) if eleve else None,
        })

    def _build_moyennes(self, eleve):
        """Calcule les moyennes par matière, les moyennes de semestre/annuelle
        et le rang de l'élève dans sa classe (semestriel et annuel)."""
        semestres = list(eleve.classe.annee_scolaire.semestres.all())
        resultats = []

        for semestre in semestres:
            lignes_matieres = []
            for cm in eleve.classe.classe_matieres.select_related("matiere"):
                moy_i = aggregations.moy_i_eleve_matiere_semestre(eleve, cm, semestre)
                moy_m = aggregations.moy_m_eleve_matiere_semestre(eleve, cm, semestre)
                moy_mc = aggregations.moy_mc_eleve_matiere_semestre(eleve, cm, semestre)
                if moy_m is not None:
                    lignes_matieres.append({
                        "matiere": cm.matiere.nom,
                        "coefficient": cm.coefficient,
                        "moy_i": moy_i,
                        "moy_m": moy_m,
                        "moy_mc": moy_mc,
                    })
            moy_semestre = aggregations.moy_semestre_eleve(eleve, semestre)
            # Conduite validée : affichée comme une ligne à part entière
            # du tableau (coefficient 1, pas d'interro ni devoir).
            conduite = eleve.conduites.filter(semestre=semestre, valide=True).first()
            # Rang semestriel : calculé pour toute la classe (notes
            # validées uniquement), ex æquo compris. None si l'élève
            # n'a aucune moyenne validée ce semestre (donc pas classé).
            rangs = aggregations.rangs_semestriels_classe(eleve.classe, semestre)
            rang = None
            if eleve.pk in rangs:
                rang = {"rang": rangs[eleve.pk], "total": len(rangs)}
            resultats.append({
                "semestre": semestre,
                "lignes": lignes_matieres,
                "moyenne": moy_semestre,
                "conduite": conduite.note if conduite else None,
                "rang": rang,
                # Totaux pour la ligne « Total » du tableau : somme des
                # coefficients et somme des moyennes coefficientées des
                # lignes affichées (+ conduite, coefficient 1, si validée).
                "total_coefficients": (
                    sum(
                        (ligne["coefficient"] for ligne in lignes_matieres),
                        start=0,
                    )
                    + (Conduite.COEFFICIENT if conduite is not None else 0)
                ),
                "total_moy_mc": (
                    sum(
                        (
                            ligne["moy_mc"]
                            for ligne in lignes_matieres
                            if ligne["moy_mc"] is not None
                        ),
                        Decimal(0),
                    )
                    + (conduite.note if conduite is not None else Decimal(0))
                ),
            })

        # Moyenne annuelle + rang annuel
        rang_annuel = None
        if len(semestres) >= 2:
            moy_annuelle = aggregations.moy_annuelle_eleve(eleve, semestres[0], semestres[1])
            rangs_annuels = aggregations.rangs_annuels_classe(
                eleve.classe, semestres[0], semestres[1]
            )
            if eleve.pk in rangs_annuels:
                rang_annuel = {"rang": rangs_annuels[eleve.pk], "total": len(rangs_annuels)}
        else:
            moy_annuelle = None

        return {
            "semestres": resultats,
            "moy_annuelle": moy_annuelle,
            "rang_annuel": rang_annuel,
        }