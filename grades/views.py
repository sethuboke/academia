from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from academics.models import Classe, ClasseMatiere, Eleve, Semestre

from . import aggregations
from .forms import NoteFormSet
from .models import Conduite, Devoir, Interrogation, MAX_INTERROS_PAR_PERIODE


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


class SaisieConduiteView(LoginRequiredMixin, View):
    """
    Saisie groupée de la conduite pour une classe et un semestre donnés
    (une ligne par élève). La conduite n'a ni interrogation ni devoir :
    c'est une note directe, comptée avec un coefficient 1 dans la
    moyenne semestrielle. Une nouvelle saisie met à jour la conduite
    existante de l'élève.
    """
    template_name = "grades/saisie_conduite.html"

    def get_classe_semestre(self, classe_pk, semestre_pk):
        classe = get_object_or_404(Classe.objects.select_related("annee_scolaire"), pk=classe_pk)
        semestre = get_object_or_404(Semestre, pk=semestre_pk)
        return classe, semestre

    def build_initial(self, classe, semestre):
        # Préremplit les conduites déjà saisies pour faciliter la modification.
        conduites = dict(
            Conduite.objects.filter(eleve__classe=classe, semestre=semestre).values_list(
                "eleve_id", "note"
            )
        )
        return [
            {"eleve_id": e.pk, "eleve_nom": str(e), "note": conduites.get(e.pk)}
            for e in classe.eleves.all()
        ]

    def get(self, request, classe_pk, semestre_pk):
        classe, semestre = self.get_classe_semestre(classe_pk, semestre_pk)
        formset = NoteFormSet(initial=self.build_initial(classe, semestre))
        nb_a_valider = Conduite.objects.filter(
            eleve__classe=classe, semestre=semestre, valide=False
        ).count()
        return render(request, self.template_name, {
            "classe": classe, "semestre": semestre, "formset": formset,
            "nb_a_valider": nb_a_valider,
        })

    def post(self, request, classe_pk, semestre_pk):
        classe, semestre = self.get_classe_semestre(classe_pk, semestre_pk)
        formset = NoteFormSet(request.POST, initial=self.build_initial(classe, semestre))
        if formset.is_valid():
            erreurs = []
            nb_enregistrees = 0
            for form in formset:
                note = form.cleaned_data.get("note")
                eleve_id = form.cleaned_data.get("eleve_id")
                if note is None or eleve_id is None:
                    continue  # ligne laissée vide : pas de conduite à enregistrer
                try:
                    Conduite.objects.update_or_create(
                        eleve_id=eleve_id, semestre=semestre, defaults={"note": note},
                    )
                    nb_enregistrees += 1
                except ValidationError as exc:
                    eleve = Eleve.objects.filter(pk=eleve_id).first()
                    nom_eleve = str(eleve) if eleve else f"Élève #{eleve_id}"
                    erreurs.append(f"{nom_eleve} : {exc}")
            if nb_enregistrees:
                messages.success(request, f"{nb_enregistrees} conduite(s) enregistrée(s).")
            for erreur in erreurs:
                messages.error(request, erreur)
            return redirect(
                "grades:saisie_conduite", classe_pk=classe.pk, semestre_pk=semestre.pk
            )
        return render(request, self.template_name, {
            "classe": classe, "semestre": semestre, "formset": formset,
        })


class ValiderConduitesView(LoginRequiredMixin, View):
    """
    Rend consultables par les élèves toutes les conduites non encore
    validées d'une classe pour un semestre donné (même principe que
    ValiderNotesView pour les interrogations et devoirs).
    """

    def post(self, request, classe_pk, semestre_pk):
        classe = get_object_or_404(Classe, pk=classe_pk)
        semestre = get_object_or_404(Semestre, pk=semestre_pk)
        nb = Conduite.objects.filter(
            eleve__classe=classe, semestre=semestre, valide=False
        ).update(valide=True, date_validation=timezone.now())
        if nb:
            messages.success(request, f"{nb} conduite(s) validée(s) et visibles par les élèves.")
        else:
            messages.info(request, "Aucune conduite à valider.")
        return redirect("grades:saisie_conduite", classe_pk=classe.pk, semestre_pk=semestre.pk)


class SaisieDevoirView(_SaisieNotesBaseView):
    def dispatch(self, request, *args, **kwargs):
        # On retire "numero" des kwargs pour qu'il ne soit pas transmis à
        # get()/post() de la classe de base (qui ne l'accepte pas).
        self.numero = kwargs.pop("numero")
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
            nb_interros = interros.count()
            nb_devoirs = devoirs.count()
            lignes.append({
                "eleve": eleve, "interros": interros, "devoirs": devoirs, "moyenne": moyenne,
                # Statut : "Complet" uniquement lorsque les 2 interrogations
                # et les 2 devoirs sont saisis.
                "complet": nb_interros >= 2 and nb_devoirs == 2,
                "a_des_notes": nb_interros > 0 or nb_devoirs > 0,
            })

        reste_a_valider = (
            Interrogation.objects.filter(classe_matiere=classe_matiere, semestre=semestre, valide=False).exists()
            or Devoir.objects.filter(classe_matiere=classe_matiere, semestre=semestre, valide=False).exists()
        )

        return render(request, self.template_name, {
            "classe_matiere": classe_matiere, "semestre": semestre,
            "lignes": lignes, "reste_a_valider": reste_a_valider,
        })

class BilanEleveView(LoginRequiredMixin, View):
    """
    Bilan complet d'un élève côté administration : toutes les matières,
    tous les semestres, conduite, moyennes semestrielles et annuelle, rangs.

    Différence avec la consultation publique élève (student_access) :
    - l'admin voit AUSSI les notes non encore validées (affichées avec un
      badge distinct) ;
    - les moyennes affichées intègrent donc toutes les notes saisies,
      tandis que les rangs restent calculés sur les seules notes validées
      (même règle que le bulletin consulté par l'élève).
    """
    template_name = "grades/bilan_eleve.html"

    def get(self, request, pk):
        eleve = get_object_or_404(
            Eleve.objects.select_related("classe", "classe__annee_scolaire"), pk=pk
        )
        classe = eleve.classe
        semestres = list(classe.annee_scolaire.semestres.all())

        resultats = []
        for semestre in semestres:
            lignes = []
            for cm in classe.classe_matieres.select_related("matiere"):
                interros = Interrogation.objects.filter(
                    eleve=eleve, classe_matiere=cm, semestre=semestre
                ).order_by("date_saisie")
                devoirs = Devoir.objects.filter(
                    eleve=eleve, classe_matiere=cm, semestre=semestre
                ).order_by("numero")

                # Toutes les matières de la classe sont affichées ; une
                # matière sans note aura simplement des tirets (moyennes
                # à None) et n'entrera pas dans le total des MC.

                # Affichage en colonnes : une case par interrogation
                # (I1 à I4, complétées par des cases vides) puis D1 et D2,
                # chacune avec son statut de validation.
                interros_cells = [
                    {"note": i.note, "valide": i.valide} for i in interros
                ]
                interros_cells += [None] * (
                    MAX_INTERROS_PAR_PERIODE - len(interros_cells)
                )
                devoirs_par_numero = {d.numero: d for d in devoirs}
                devoirs_cells = []
                for numero in (1, 2):
                    devoir = devoirs_par_numero.get(numero)
                    devoirs_cells.append(
                        {"note": devoir.note, "valide": devoir.valide}
                        if devoir else None
                    )

                lignes.append({
                    "matiere": cm.matiere.nom,
                    "coefficient": cm.coefficient,
                    "interros_cells": interros_cells,
                    "devoirs_cells": devoirs_cells,
                    # Toutes les notes sont prises en compte pour l'admin.
                    "moy_i": aggregations.moy_i_eleve_matiere_semestre(
                        eleve, cm, semestre, seulement_validees=False
                    ),
                    "moy_m": aggregations.moy_m_eleve_matiere_semestre(
                        eleve, cm, semestre, seulement_validees=False
                    ),
                    "moy_mc": aggregations.moy_mc_eleve_matiere_semestre(
                        eleve, cm, semestre, seulement_validees=False
                    ),
                    "a_non_validees": (
                        interros.filter(valide=False).exists()
                        or devoirs.filter(valide=False).exists()
                    ),
                })

            conduite = eleve.conduites.filter(semestre=semestre).first()
            rangs = aggregations.rangs_semestriels_classe(classe, semestre)
            rang = None
            if eleve.pk in rangs:
                rang = {"rang": rangs[eleve.pk], "total": len(rangs)}
            # Totaux du tableau : Σ coefficients et Σ moyennes coefficiées
            # des matières affichées, plus la conduite (coefficient 1, sa
            # note joue le rôle d'une moyenne déjà coefficiée) lorsqu'elle
            # est saisie. Les matières sans note (moy_mc=None) sont exclues
            # du total des MC, comme dans moyenne_semestre.
            total_coefficients = sum(l["coefficient"] for l in lignes)
            mc_pertinentes = [l["moy_mc"] for l in lignes if l["moy_mc"] is not None]
            if conduite:
                total_coefficients += Conduite.COEFFICIENT
                mc_pertinentes.append(conduite.note)
            total_moy_mc = (
                sum(mc_pertinentes) if mc_pertinentes else None
            )

            resultats.append({
                "semestre": semestre,
                "lignes": lignes,
                "total_coefficients": total_coefficients,
                "total_moy_mc": total_moy_mc,
                "conduite": conduite.note if conduite else None,
                "conduite_validee": conduite.valide if conduite else False,
                "moyenne": aggregations.moy_semestre_eleve(
                    eleve, semestre, seulement_validees=False
                ),
                "rang": rang,
                "a_notes_non_validees": any(l["a_non_validees"] for l in lignes)
                or (conduite is not None and not conduite.valide),
            })

        # Moyenne annuelle + rang annuel
        rang_annuel = None
        if len(semestres) >= 2:
            moy_annuelle = aggregations.moy_annuelle_eleve(
                eleve, semestres[0], semestres[1], seulement_validees=False
            )
            rangs_annuels = aggregations.rangs_annuels_classe(
                classe, semestres[0], semestres[1]
            )
            if eleve.pk in rangs_annuels:
                rang_annuel = {
                    "rang": rangs_annuels[eleve.pk],
                    "total": len(rangs_annuels),
                }
        else:
            moy_annuelle = None

        return render(request, self.template_name, {
            "eleve": eleve,
            "classe": classe,
            "resultats": resultats,
            "moy_annuelle": moy_annuelle,
            "rang_annuel": rang_annuel,
        })


def _cle_tri_merite(ligne, afficher_annuel):
    """Clé de tri de la fiche « ordre des mérites » : les élèves classés
    par mérite croissant d'abord, les non classés (sans moyenne) ensuite.
    Accepte le rang sous forme de dict {"rang": n, "total": m} (vue HTML)
    ou d'entier brut (vue PDF)."""
    rang = ligne["rang_annuel"] if afficher_annuel else ligne["rang"]
    if rang is None:
        return (True, 0)
    valeur = rang["rang"] if isinstance(rang, dict) else rang
    return (False, valeur)


def _construire_sections_statistiques(classe, classe_matieres, semestres):
    """
    Construit les sections (une par semestre) partagées entre l'écran
    « Bilan semestriel » et la page « Statistique — Ordre des mérites ».

    Chaque section contient :
    - semestre : le semestre concerné ;
    - lignes   : une ligne par élève (moyennes coefficiées par matière,
      total, moyenne semestrielle, rang) ;
    - afficher_annuel : True pour la table du second semestre d'une
      année complète (colonnes Moyenne annuelle / Rang annuel) ;
    - fiche    : les mêmes lignes triées par ordre des mérites — rang
      semestriel pour S1, rang ANNUEL pour le second semestre (les
      élèves non classés restent en fin).

    Comme pour BilanEleveView (côté administration), TOUTES les notes —
    validées ou non — sont prises en compte. Les mêmes fonctions
    d'agrégation que le bulletin individuel sont réutilisées afin que
    les moyennes et rangs restent cohérents entre les deux écrans.
    """
    eleves = list(classe.eleves.order_by("nom", "prenom"))
    avec_annuel = len(semestres) >= 2

    # Rangs calculés UNE fois par semestre/classe puis consultés
    # ligne par ligne (évite de relancer le classement par élève).
    rangs_semestriels = {
        semestre.pk: aggregations.rangs_semestriels_classe(
            classe, semestre, seulement_validees=False
        )
        for semestre in semestres
    }
    rangs_annuels = (
        aggregations.rangs_annuels_classe(
            classe, semestres[0], semestres[1], seulement_validees=False
        )
        if avec_annuel
        else {}
    )

    sections = []
    for index, semestre in enumerate(semestres):
        # Les colonnes annuelles ne concernent que la table du
        # second semestre (dernier semestre d'une année complète).
        afficher_annuel = avec_annuel and index == len(semestres) - 1
        rangs = rangs_semestriels[semestre.pk]

        lignes = []
        for eleve in eleves:
            cellules = []
            total = None  # Σ des moyennes coefficientées des matières
            for cm in classe_matieres:
                moy_mc = aggregations.moy_mc_eleve_matiere_semestre(
                    eleve, cm, semestre, seulement_validees=False
                )
                cellules.append(moy_mc)
                if moy_mc is not None:
                    total = moy_mc if total is None else total + moy_mc

            ligne = {
                "eleve": eleve,
                "est_fille": eleve.genre == Eleve.Genre.FEMININ,
                "cellules": cellules,
                "total": total,
                "moyenne": aggregations.moy_semestre_eleve(
                    eleve, semestre, seulement_validees=False
                ),
                "rang": (
                    {"rang": rangs[eleve.pk], "total": len(rangs)}
                    if eleve.pk in rangs
                    else None
                ),
            }
            if afficher_annuel:
                ligne["moy_annuelle"] = aggregations.moy_annuelle_eleve(
                    eleve, semestres[0], semestres[1],
                    seulement_validees=False,
                )
                ligne["rang_annuel"] = (
                    {"rang": rangs_annuels[eleve.pk], "total": len(rangs_annuels)}
                    if eleve.pk in rangs_annuels
                    else None
                )
            lignes.append(ligne)

        sections.append({
            "semestre": semestre,
            "lignes": lignes,
            "afficher_annuel": afficher_annuel,
            "fiche": sorted(
                lignes,
                key=lambda l: _cle_tri_merite(l, afficher_annuel),
            ),
        })
    return sections


class ClasseBilanView(LoginRequiredMixin, View):
    """
    Bilan semestriel d'une classe entière : une ligne par élève, une
    colonne par matière affectée (moyenne coefficiée), puis les colonnes
    Total, Moyenne semestrielle et Rang. Pour le second semestre d'une
    année à deux semestres, deux colonnes supplémentaires : Moyenne
    annuelle et Rang annuel.

    Comme pour BilanEleveView (côté administration), TOUTES les notes —
    validées ou non — sont prises en compte. Les mêmes fonctions
    d'agrégation que le bulletin individuel sont réutilisées afin que
    les moyennes et rangs restent cohérents entre les deux écrans.
    """

    template_name = "grades/bilan_classe.html"

    def get(self, request, pk):
        classe = get_object_or_404(
            Classe.objects.select_related("annee_scolaire"), pk=pk
        )
        classe_matieres = list(classe.classe_matieres.select_related("matiere"))
        semestres = list(classe.annee_scolaire.semestres.all())
        sections = _construire_sections_statistiques(
            classe, classe_matieres, semestres
        )

        return render(request, self.template_name, {
            "classe": classe,
            "classe_matieres": classe_matieres,
            "sections": sections,
        })


class ClasseStatistiqueView(LoginRequiredMixin, View):
    """
    Page « Statistique — Ordre des mérites » d'une classe : pour chaque
    semestre, le tableau des apprenants classés par mérite (rang
    semestriel pour le premier semestre, rang ANNUEL pour le second
    semestre d'une année complète), téléchargeable en PDF.

    La table détaillée des moyennes par matière reste sur la page
    « Bilan semestriel » (grades.views.ClasseBilanView).
    """

    template_name = "grades/statistique_classe.html"

    def get(self, request, pk):
        classe = get_object_or_404(
            Classe.objects.select_related("annee_scolaire"), pk=pk
        )
        classe_matieres = list(classe.classe_matieres.select_related("matiere"))
        semestres = list(classe.annee_scolaire.semestres.all())
        sections = _construire_sections_statistiques(
            classe, classe_matieres, semestres
        )

        return render(request, self.template_name, {
            "classe": classe,
            "classe_matieres": classe_matieres,
            "sections": sections,
        })


class ClasseBilanPdfView(LoginRequiredMixin, View):
    """
    Fiche statistique « Ordre des mérites » d'une classe pour un semestre
    donné, téléchargeable en PDF.

    - Premier semestre (ou année à un seul semestre) : Mérite | Nom &
      Prénom | Moyenne semestrielle.
    - Second semestre : le mérite est le RANG ANNUEL et une colonne
      Moyenne annuelle s'ajoute.

    Les informations des filles sont composées en gras.
    """

    def get(self, request, pk, semestre_pk):
        classe = get_object_or_404(
            Classe.objects.select_related("annee_scolaire"), pk=pk
        )
        semestre = get_object_or_404(Semestre, pk=semestre_pk)
        if semestre.annee_scolaire_id != classe.annee_scolaire_id:
            raise Http404("Ce semestre n'appartient pas à l'année scolaire de la classe.")

        semestres = list(classe.annee_scolaire.semestres.all())
        avec_annuel = len(semestres) >= 2
        # Le second semestre (dernier d'une année complète) utilise le rang annuel.
        afficher_annuel = avec_annuel and semestres[-1].pk == semestre.pk

        rangs = aggregations.rangs_semestriels_classe(
            classe, semestre, seulement_validees=False
        )
        rangs_annuels = (
            aggregations.rangs_annuels_classe(
                classe, semestres[0], semestres[1], seulement_validees=False
            )
            if avec_annuel
            else {}
        )

        lignes = []
        for eleve in classe.eleves.order_by("nom", "prenom"):
            ligne = {
                "eleve": eleve,
                "est_fille": eleve.genre == Eleve.Genre.FEMININ,
                "moyenne": aggregations.moy_semestre_eleve(
                    eleve, semestre, seulement_validees=False
                ),
                "rang": rangs.get(eleve.pk),
            }
            if afficher_annuel:
                ligne["moy_annuelle"] = aggregations.moy_annuelle_eleve(
                    eleve, semestres[0], semestres[1], seulement_validees=False
                )
                ligne["rang_annuel"] = rangs_annuels.get(eleve.pk)
            lignes.append(ligne)
        lignes.sort(key=lambda l: _cle_tri_merite(l, afficher_annuel))
        return self._rendre_pdf(request, classe, semestre, lignes, afficher_annuel)

    def _rendre_pdf(self, request, classe, semestre, lignes, afficher_annuel):
        import io

        from django.http import HttpResponse
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            title=f"Ordre des mérites — {classe.nom}",
            topMargin=15 * mm, bottomMargin=15 * mm,
            leftMargin=15 * mm, rightMargin=15 * mm,
        )
        styles = getSampleStyleSheet()
        style_titre = ParagraphStyle(
            "TitreFiche", parent=styles["Title"], fontSize=16
        )
        style_sous_titre = ParagraphStyle(
            "SousTitreFiche", parent=styles["Normal"], fontSize=10,
            alignment=1, textColor=colors.HexColor("#475569"),
        )

        entetes = ["Mérite", "Nom & Prénom", "Moyenne semestrielle"]
        if afficher_annuel:
            entetes.append("Moyenne annuelle")

        donnees = [entetes]
        lignes_filles = []  # index (dans la table, entête inclus) à composer en gras
        for position, l in enumerate(lignes, start=1):
            rang = l["rang_annuel"] if afficher_annuel else l["rang"]
            cellules = [
                str(rang) if rang else "—",
                f"{l['eleve'].nom} {l['eleve'].prenom}",
                str(l["moyenne"]) if l["moyenne"] is not None else "—",
            ]
            if afficher_annuel:
                cellules.append(
                    str(l["moy_annuelle"]) if l["moy_annuelle"] is not None else "—"
                )
            donnees.append(cellules)
            if l["est_fille"]:
                lignes_filles.append(position)

        table = Table(
            donnees,
            colWidths=[25 * mm, 80 * mm, 45 * mm] + ([35 * mm] if afficher_annuel else []),
        )
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        for index_fille in lignes_filles:
            style.append(("FONTNAME", (0, index_fille), (-1, index_fille), "Helvetica-Bold"))
        table.setStyle(TableStyle(style))

        legende = (
            "Ordre des mérites fondé sur le rang annuel"
            if afficher_annuel
            else "Ordre des mérites fondé sur la moyenne semestrielle"
        )
        doc.build([
            Paragraph("Fiche statistique — Ordre des mérites", style_titre),
            Paragraph(
                f"{classe.nom} — Année scolaire {classe.annee_scolaire.libelle}"
                f" — {semestre.get_libelle_display()}",
                style_sous_titre,
            ),
            Spacer(1, 4 * mm),
            table,
            Spacer(1, 4 * mm),
            Paragraph(legende + ". Les résultats des filles sont en gras.", style_sous_titre),
        ])

        pdf = buffer.getvalue()
        buffer.close()

        # Nom de fichier ASCII (l'en-tête Content-Disposition ne supporte
        # pas l'UTF-8) : on supprime les accents/diacritiques.
        import unicodedata

        brut = (
            f"fiche-merites-{classe.nom}-{semestre.libelle}-"
            f"{classe.annee_scolaire.libelle}.pdf"
        )
        nom_fichier = (
            unicodedata.normalize("NFKD", brut)
            .encode("ascii", "ignore")
            .decode("ascii")
            .replace(" ", "_")
        )
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{nom_fichier}"'
        return response
