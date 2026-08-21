from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

from academics.models import Eleve, ClasseMatiere, Semestre

# Hypothèse : notation sur 20 (système francophone standard).
# À ajuster si une autre échelle est utilisée.
NOTE_VALIDATORS = [MinValueValidator(0), MaxValueValidator(20)]

MAX_INTERROS_PAR_PERIODE = 4
DEVOIR_NUMEROS = [(1, "Devoir 1"), (2, "Devoir 2")]


class EvaluationBase(models.Model):
    """Champs communs à Interrogation et Devoir."""
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name="%(class)s_set")
    classe_matiere = models.ForeignKey(
        ClasseMatiere, on_delete=models.CASCADE, related_name="%(class)s_set"
    )
    semestre = models.ForeignKey(Semestre, on_delete=models.CASCADE, related_name="%(class)s_set")
    note = models.DecimalField(max_digits=4, decimal_places=2, validators=NOTE_VALIDATORS)

    date_saisie = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    valide = models.BooleanField(default=False)
    date_validation = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def clean(self):
        # L'élève doit appartenir à la même classe que la ClasseMatiere visée.
        if self.eleve_id and self.classe_matiere_id:
            if self.eleve.classe_id != self.classe_matiere.classe_id:
                raise ValidationError(
                    "L'élève ne fait pas partie de la classe associée à cette matière."
                )
        # Le semestre doit appartenir à la même année scolaire que la classe.
        if self.semestre_id and self.classe_matiere_id:
            if self.semestre.annee_scolaire_id != self.classe_matiere.classe.annee_scolaire_id:
                raise ValidationError(
                    "Le semestre ne correspond pas à l'année scolaire de la classe."
                )

    def save(self, *args, **kwargs):
        # Toute modification postérieure à la validation doit rester tracée
        # (l'horodatage vient de date_modification ; le détail de l'action
        # est loggé côté vue/signal dans l'app audit).
        if self.valide and not self.date_validation:
            from django.utils import timezone

            self.date_validation = timezone.now()
        self.full_clean()
        super().save(*args, **kwargs)


class Interrogation(EvaluationBase):
    """
    Une interrogation individuelle. Il peut y en avoir 1 à 4 par
    (élève, matière de classe, semestre) — voir §5.3 du CDC (Moy_I).
    """

    class Meta(EvaluationBase.Meta):
        abstract = False
        constraints = [
            models.UniqueConstraint(
                fields=["eleve", "classe_matiere", "semestre", "date_saisie"],
                name="uniq_interro_par_instant",
            )
        ]
        ordering = ["eleve", "classe_matiere", "semestre", "date_saisie"]

    def clean(self):
        super().clean()
        if self.eleve_id and self.classe_matiere_id and self.semestre_id:
            qs = Interrogation.objects.filter(
                eleve=self.eleve,
                classe_matiere=self.classe_matiere,
                semestre=self.semestre,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.count() >= MAX_INTERROS_PAR_PERIODE:
                raise ValidationError(
                    f"Maximum {MAX_INTERROS_PAR_PERIODE} interrogations par matière "
                    f"et par semestre pour cet élève."
                )

    def __str__(self):
        return f"Interro {self.note}/20 — {self.eleve} — {self.classe_matiere.matiere}"


class Devoir(EvaluationBase):
    """
    Devoir 1 ou 2 par (élève, matière de classe, semestre) — voir §5.3 (Moy_M).
    Si un seul des deux devoirs existe, la moyenne matière se calcule
    en moyenne partielle sur ce qui est disponible (décision produit).
    """
    numero = models.PositiveSmallIntegerField(choices=DEVOIR_NUMEROS)

    class Meta(EvaluationBase.Meta):
        abstract = False
        constraints = [
            models.UniqueConstraint(
                fields=["eleve", "classe_matiere", "semestre", "numero"],
                name="uniq_devoir_par_numero",
            ),
            models.CheckConstraint(
                condition=models.Q(numero__in=[1, 2]), name="devoir_numero_valide"
            ),
        ]
        ordering = ["eleve", "classe_matiere", "semestre", "numero"]

    def __str__(self):
        return f"Devoir {self.numero} — {self.note}/20 — {self.eleve} — {self.classe_matiere.matiere}"