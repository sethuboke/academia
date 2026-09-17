from django.db import models
from django.utils import timezone

from academics.models import Eleve


class Sanction(models.Model):
    """Sanction disciplinaire infligée à un apprenant indiscipliné."""

    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name="sanctions")
    date = models.DateField(default=timezone.localdate, verbose_name="Date")
    motif = models.CharField(
        max_length=255,
        verbose_name="Motif",
        help_text="Motif de la sanction (ex : perturbation en classe).",
    )
    sanction = models.CharField(
        max_length=255,
        verbose_name="Sanction",
        help_text="Sanction appliquée (ex : avertissement, blâme, exclusion…).",
    )

    class Meta:
        ordering = ["-date"]
        verbose_name = "Sanction"
        verbose_name_plural = "Sanctions"

    def __str__(self):
        return f"{self.sanction} — {self.eleve} — {self.date}"