from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from academics.models import AnneeScolaire, Classe, Eleve

from .models import Sanction


class SanctionModelTests(TestCase):
    def test_creation_sanction(self):
        annee = AnneeScolaire.objects.create(libelle="2025-2026")
        classe = Classe.objects.create(annee_scolaire=annee, nom="Seconde C")
        eleve = Eleve.objects.create(
            classe=classe, nom="Kossi", prenom="Abla",
            statut=Eleve.Statut.NOUVEAU, genre=Eleve.Genre.FEMININ,
        )
        sanction = Sanction.objects.create(
            eleve=eleve,
            date=date(2026, 1, 15),
            motif="Perturbation en classe",
            sanction="Avertissement",
        )
        self.assertEqual(
            str(sanction), "Avertissement — Kossi Abla — Seconde C (2025-2026) — 2026-01-15",
        )
        self.assertEqual(eleve.sanctions.count(), 1)


class SanctionViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("prof", password="pass12345")
        cls.annee = AnneeScolaire.objects.create(libelle="2025-2026")
        cls.classe = Classe.objects.create(annee_scolaire=cls.annee, nom="Terminale A")
        cls.eleve = Eleve.objects.create(
            classe=cls.classe, nom="Adjoua", prenom="Estelle",
            statut=Eleve.Statut.NOUVEAU, genre=Eleve.Genre.FEMININ,
        )

    def setUp(self):
        self.client.login(username="prof", password="pass12345")

    def test_page_sanctions_accesible(self):
        url = reverse("sanctions:sanction_list", args=[self.classe.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nouvelle sanction")

    def test_creation_sanction_via_formulaire(self):
        url = reverse("sanctions:sanction_list", args=[self.classe.pk])
        response = self.client.post(url, {
            "eleve": self.eleve.pk,
            "date": "2026-01-15",
            "motif": "Manque de respect envers un enseignant",
            "sanction": "Blâme",
        })
        self.assertRedirects(response, url)
        self.assertEqual(Sanction.objects.count(), 1)
        sanction = Sanction.objects.get()
        self.assertEqual(sanction.eleve, self.eleve)
        self.assertEqual(sanction.motif, "Manque de respect envers un enseignant")
        self.assertEqual(sanction.sanction, "Blâme")

    def test_historique_visible(self):
        Sanction.objects.create(
            eleve=self.eleve, date=date(2026, 1, 15),
            motif="Perturbation", sanction="Avertissement",
        )
        url = reverse("sanctions:sanction_list", args=[self.classe.pk])
        response = self.client.get(url)
        self.assertContains(response, "Avertissement")
        self.assertContains(response, "Perturbation")

    def test_suppression_sanction(self):
        sanction = Sanction.objects.create(
            eleve=self.eleve, date=date(2026, 1, 15),
            motif="Perturbation", sanction="Avertissement",
        )
        url = reverse("sanctions:sanction_delete", args=[sanction.pk])
        self.client.post(url)
        self.assertEqual(Sanction.objects.count(), 0)

    def test_eleve_hors_classe_exclu_du_formulaire(self):
        autre_annee = AnneeScolaire.objects.create(libelle="2024-2025")
        autre_classe = Classe.objects.create(annee_scolaire=autre_annee, nom="Première C")
        autre_eleve = Eleve.objects.create(
            classe=autre_classe, nom="Autre", prenom="Elève",
            statut=Eleve.Statut.NOUVEAU, genre=Eleve.Genre.MASCULIN,
        )
        url = reverse("sanctions:sanction_list", args=[self.classe.pk])
        response = self.client.post(url, {
            "eleve": autre_eleve.pk,  # hors de la classe : doit être refusé
            "date": "2026-01-15",
            "motif": "Test",
            "sanction": "Blâme",
        })
        self.assertEqual(response.status_code, 200)  # formulaire invalide
        self.assertEqual(Sanction.objects.count(), 0)

    def test_sans_authentification_redirection_login(self):
        self.client.logout()
        url = reverse("sanctions:sanction_list", args=[self.classe.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)