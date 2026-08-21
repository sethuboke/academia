from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from academics.models import ClasseMatiere, Eleve, Semestre

from . import aggregations
from .forms import NoteFormSet
from .models import Devoir, Interrogation


class _SaisieNotesBaseView(LoginRequiredMixin, View):
    """
    Base commune pour la saisie groupée d'interrogations et de devoirs :
    même écran (une ligne par élève), seul le modèle cible et les
    champs supplémentaires (numéro du devoir) changent.
    """
    template_name = "grades/saisie_notes.html"
    type_note = None  # à définir dans les sous-classes, pour l'affichage

    def get_classe_matiere_semestre(self, classe_matiere_pk, semestre_pk):
        classe_matiere = get_object_or_404(
            ClasseMatiere.objects.select_related("classe", "matiere"), pk=classe_matiere_pk
        )
        semestre = get_object_or_404(Semestre, pk=semestre_pk)
        return classe_matiere, semestre

    def build_initial(self, classe_matiere):
        return [
            {"eleve_id": e.pk, "eleve_nom": str(e), "note": None}
            for e in classe_matiere.classe.eleves.all()
        ]

    def save_note(self, eleve_id, classe_matiere, semestre, note):
        raise NotImplementedError

    def get(self, request, classe_matiere_pk, semestre_pk):
        classe_matiere, semestre = self.get_classe_matiere_semestre(classe_matiere_pk, semestre_pk)
        formset = NoteFormSet(initial=self.build_initial(classe_matiere))
        return render(request, self.template_name, {
            "classe_matiere": classe_matiere, "semestre": semestre,
            "formset": formset, "type_note": self.type_note,
        })

    def post(self, request, classe_matiere_pk, semestre_pk):
        classe_matiere, semestre = self.get_classe_matiere_semestre(classe_matiere_pk, semestre_pk)
        formset = NoteFormSet(request.POST, initial=self.build_initial(classe_matiere))
        if formset.is_valid():
            erreurs = []
            nb_enregistrees = 0
            for form in formset:
                note = form.cleaned_data.get("note")
                eleve_id = form.cleaned_data.get("eleve_id")
                if note is None or eleve_id is None:
                    continue  # ligne laissée vide : rien à saisir pour cet élève
                try:
                    self.save_note(eleve_id, classe_matiere, semestre, note)
                    nb_enregistrees += 1
                except Exception as exc:  # ValidationError du modèle (ex: 5e interro)
                    eleve = Eleve.objects.filter(pk=eleve_id).first()
                    nom_eleve = str(eleve) if eleve else f"Élève #{eleve_id}"
                    erreurs.append(f"{nom_eleve} : {exc}")
            if nb_enregistrees:
                messages.success(request, f"{nb_enregistrees} note(s) enregistrée(s).")
            for erreur in erreurs:
                messages.error(request, erreur)
            return redirect(
                "grades:releve_notes", classe_matiere_pk=classe_matiere.pk, semestre_pk=semestre.pk
            )
        return render(request, self.template_name, {
            "classe_matiere": classe_matiere, "semestre": semestre,
            "formset": formset, "type_note": self.type_note,
        })


class SaisieInterrogationView(_SaisieNotesBaseView):
    type_note = "Interrogation"

    def save_note(self, eleve_id, classe_matiere, semestre, note):
        Interrogation.objects.create(
            eleve_id=eleve_id, classe_matiere=classe_matiere, semestre=semestre, note=note,
        )


class SaisieDevoirView(_SaisieNotesBaseView):
    def dispatch(self, request, *args, **kwargs):
        self.numero = kwargs["numero"]
        self.type_note = f"Devoir {self.numero}"
        return super().dispatch(request, *args, **kwargs)

    def save_note(self, eleve_id, classe_matiere, semestre, note):
        Devoir.objects.update_or_create(
            eleve_id=eleve_id, classe_matiere=classe_matiere, semestre=semestre,
            numero=self.numero, defaults={"note": note},
        )


class ValiderNotesView(LoginRequiredMixin, View):
    """
    Rend consultables par les élèves toutes les notes non encore validées
    d'une matière/semestre. L'horodatage (date_validation) est posé
    automatiquement par Interrogation.save()/Devoir.save() au moment du
    passage à valide=True.
    """

    def post(self, request, classe_matiere_pk, semestre_pk):
        classe_matiere = get_object_or_404(ClasseMatiere, pk=classe_matiere_pk)
        semestre = get_object_or_404(Semestre, pk=semestre_pk)

        a_valider = list(
            Interrogation.objects.filter(classe_matiere=classe_matiere, semestre=semestre, valide=False)
        ) + list(
            Devoir.objects.filter(classe_matiere=classe_matiere, semestre=semestre, valide=False)
        )
        for note in a_valider:
            note.valide = True
            note.save()

        messages.success(request, f"{len(a_valider)} note(s) validée(s) et visibles par les élèves.")
        return redirect("grades:releve_notes", classe_matiere_pk=classe_matiere.pk, semestre_pk=semestre.pk)


class ReleveNotesView(LoginRequiredMixin, View):
    """Vue d'ensemble des notes (validées ou non) et de la moyenne matière par élève."""
    template_name = "grades/releve_notes.html"

    def get(self, request, classe_matiere_pk, semestre_pk):
        classe_matiere = get_object_or_404(
            ClasseMatiere.objects.select_related("classe", "matiere"), pk=classe_matiere_pk
        )
        semestre = get_object_or_404(Semestre, pk=semestre_pk)

        lignes = []
        for eleve in classe_matiere.classe.eleves.all():
            interros = Interrogation.objects.filter(
                eleve=eleve, classe_matiere=classe_matiere, semestre=semestre
            )
            devoirs = Devoir.objects.filter(
                eleve=eleve, classe_matiere=classe_matiere, semestre=semestre
            )
            moyenne = aggregations.moy_m_eleve_matiere_semestre(
                eleve, classe_matiere, semestre, seulement_validees=False
            )
            lignes.append({
                "eleve": eleve, "interros": interros, "devoirs": devoirs, "moyenne": moyenne,
            })

        reste_a_valider = (
            Interrogation.objects.filter(classe_matiere=classe_matiere, semestre=semestre, valide=False).exists()
            or Devoir.objects.filter(classe_matiere=classe_matiere, semestre=semestre, valide=False).exists()
        )

        return render(request, self.template_name, {
            "classe_matiere": classe_matiere, "semestre": semestre,
            "lignes": lignes, "reste_a_valider": reste_a_valider,
        })