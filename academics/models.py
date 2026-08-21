from django.db import models
from django.core.exceptions import ValidationError


class AnneeScolaireQuerySet(models.QuerySet):
    def courante(self):
        return self.filter(est_courante=True).first()


class AnneeScolaire(models.Model):
    """Ex: '2025-2026'. Sert de racine temporelle pour classes et semestres."""
    libelle = models.CharField(max_length=20, unique=True)
    est_courante = models.BooleanField(default=False)

    objects = AnneeScolaireQuerySet.as_manager()

    class Meta:
        ordering = ["-libelle"]

    def __str__(self):
        return self.libelle


class Semestre(models.Model):
    class Libelle(models.TextChoices):
        S1 = "S1", "Semestre 1"
        S2 = "S2", "Semestre 2"

    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.CASCADE, related_name="semestres"
    )
    libelle = models.CharField(max_length=2, choices=Libelle.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["annee_scolaire", "libelle"], name="uniq_semestre_par_annee"
            )
        ]
        ordering = ["annee_scolaire", "libelle"]

    def __str__(self):
        return f"{self.get_libelle_display()} — {self.annee_scolaire}"


class Classe(models.Model):
    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.CASCADE, related_name="classes"
    )
    nom = models.CharField(max_length=100)  # ex: "Terminale D"
    # Identifiant public non devinable pour le lien de consultation élève (§5.4 du CDC)
    lien_public_uid = models.UUIDField(unique=True, editable=False, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["annee_scolaire", "nom"], name="uniq_classe_par_annee"
            )
        ]
        ordering = ["nom"]

    def save(self, *args, **kwargs):
        if not self.lien_public_uid:
            import uuid

            self.lien_public_uid = uuid.uuid4()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nom} ({self.annee_scolaire})"


class Matiere(models.Model):
    nom = models.CharField(max_length=100, unique=True)  # ex: "Mathématiques"

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class ClasseMatiere(models.Model):
    """
    Table de liaison Classe <-> Matiere. Le coefficient est défini ici
    car il varie selon la classe/niveau, pas globalement par matière.
    """
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name="classe_matieres")
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, related_name="classe_matieres")
    coefficient = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["classe", "matiere"], name="uniq_matiere_par_classe"
            ),
            models.CheckConstraint(
                condition=models.Q(coefficient__gte=1), name="coefficient_positif"
            ),
        ]
        ordering = ["classe", "matiere"]

    def __str__(self):
        return f"{self.matiere} (coef {self.coefficient}) — {self.classe}"


class Eleve(models.Model):
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name="eleves")
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["classe", "nom", "prenom"], name="uniq_eleve_par_classe"
            )
        ]
        ordering = ["nom", "prenom"]

    def __str__(self):
        return f"{self.nom} {self.prenom} — {self.classe}"