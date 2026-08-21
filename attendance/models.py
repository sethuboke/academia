from django.db import models

from academics.models import Eleve


class Absence(models.Model):
    class Type(models.TextChoices):
        ABSENCE = "ABSENCE", "Absence"
        RETARD = "RETARD", "Retard"

    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name="absences")
    date = models.DateField()
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.ABSENCE)
    motif = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.get_type_display()} — {self.eleve} — {self.date}"