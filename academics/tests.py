from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from .models import AnneeScolaire, Classe, Eleve


class EleveBulkCreateTests(TestCase):
    """Enregistrement groupé de plusieurs apprenants."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("prof", password="pass12345")
        cls.annee = AnneeScolaire.objects.create(libelle="2025-2026", est_courante=True)
        cls.classe = Classe.objects.create(annee_scolaire=cls.annee, nom="Terminale D")

    def setUp(self):
        self.client.login(username="prof", password="pass12345")

    def test_page_enregistrement_multiple_accesible(self):
        url = reverse("academics:eleve_bulk_create", args=[self.classe.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enregistrer plusieurs apprenants")

    def test_enregistrement_de_plusieurs_apprenants(self):
        url = reverse("academics:eleve_bulk_create", args=[self.classe.pk])
        response = self.client.post(url, {
            "eleves-TOTAL_FORMS": "2",
            "eleves-INITIAL_FORMS": "0",
            "eleves-MIN_NUM_FORMS": "0",
            "eleves-MAX_NUM_FORMS": "50",
            "eleves-0-nom": "dossou",
            "eleves-0-prenom": "jean",
            "eleves-0-genre": "M",
            "eleves-0-statut": "N",
            "eleves-1-nom": "AHOUANSOU",
            "eleves-1-prenom": "mariam",
            "eleves-1-genre": "F",
            "eleves-1-statut": "R",
        })
        self.assertRedirects(response, reverse("academics:classe_detail", args=[self.classe.pk]))
        self.assertEqual(Eleve.objects.count(), 2)
        jean = Eleve.objects.get(nom="DOSSOU")
        self.assertEqual(jean.prenom, "Jean")
        self.assertEqual(jean.genre, "M")
        self.assertEqual(jean.statut, "N")
        mariam = Eleve.objects.get(nom="AHOUANSOU")
        self.assertEqual(mariam.prenom, "Mariam")
        self.assertEqual(mariam.genre, "F")
        self.assertEqual(mariam.statut, "R")

    def test_normalisation_casse_nom_majuscule_prenom_capitalise(self):
        url = reverse("academics:eleve_bulk_create", args=[self.classe.pk])
        self.client.post(url, {
            "eleves-TOTAL_FORMS": "2",
            "eleves-INITIAL_FORMS": "0",
            "eleves-MIN_NUM_FORMS": "0",
            "eleves-MAX_NUM_FORMS": "50",
            "eleves-0-nom": "doSSOU kOU",
            "eleves-0-prenom": "jean-claude marie",
            "eleves-0-genre": "M",
            "eleves-0-statut": "N",
            "eleves-1-nom": "  dossou  ",
            "eleves-1-prenom": "  jean-Marie  ",
            "eleves-1-genre": "M",
            "eleves-1-statut": "N",
        })
        # Le nom doit être entièrement en majuscules, le prénom avec la
        # première lettre de chaque partie en majuscule.
        self.assertEqual(Eleve.objects.count(), 2)
        premiere = Eleve.objects.get(prenom="Jean-Claude Marie")
        self.assertEqual(premiere.nom, "DOSSOU KOU")
        deuxieme = Eleve.objects.get(prenom="Jean-Marie")
        self.assertEqual(deuxieme.nom, "DOSSOU")

    def test_existant_dans_la_classe_non_duplique(self):
        Eleve.objects.create(
            classe=self.classe, nom="Dossou", prenom="Jean",
            statut=Eleve.Statut.NOUVEAU, genre=Eleve.Genre.MASCULIN,
        )
        url = reverse("academics:eleve_bulk_create", args=[self.classe.pk])
        response = self.client.post(url, {
            "eleves-TOTAL_FORMS": "1",
            "eleves-INITIAL_FORMS": "0",
            "eleves-MIN_NUM_FORMS": "0",
            "eleves-MAX_NUM_FORMS": "50",
            "eleves-0-nom": "DOSSOU",
            "eleves-0-prenom": "JEAN",
            "eleves-0-genre": "M",
            "eleves-0-statut": "N",
        })
        self.assertEqual(Eleve.objects.count(), 1)  # pas de doublon
        self.assertEqual(list(get_messages(response.wsgi_request))[0].tags, "warning")

    def test_lignes_vides_ignorees(self):
        url = reverse("academics:eleve_bulk_create", args=[self.classe.pk])
        self.client.post(url, {
            "eleves-TOTAL_FORMS": "3",
            "eleves-INITIAL_FORMS": "0",
            "eleves-MIN_NUM_FORMS": "0",
            "eleves-MAX_NUM_FORMS": "50",
            "eleves-0-nom": "",
            "eleves-0-prenom": "",
            "eleves-0-genre": "M",
            "eleves-0-statut": "N",
            "eleves-1-nom": "koffi",
            "eleves-1-prenom": "abla",
            "eleves-1-genre": "F",
            "eleves-1-statut": "N",
            "eleves-2-nom": "",
            "eleves-2-prenom": "",
            "eleves-2-genre": "M",
            "eleves-2-statut": "N",
        })
        self.assertEqual(Eleve.objects.count(), 1)
        eleve = Eleve.objects.get()
        self.assertEqual(eleve.nom, "KOFFI")
        self.assertEqual(eleve.prenom, "Abla")

    def test_ligne_invalide_affiche_erreur_sans_creer(self):
        url = reverse("academics:eleve_bulk_create", args=[self.classe.pk])
        response = self.client.post(url, {
            "eleves-TOTAL_FORMS": "1",
            "eleves-INITIAL_FORMS": "0",
            "eleves-MIN_NUM_FORMS": "0",
            "eleves-MAX_NUM_FORMS": "50",
            "eleves-0-nom": "Partiel",
            "eleves-0-prenom": "",  # prénom obligatoire : ligne invalide
            "eleves-0-genre": "M",
            "eleves-0-statut": "N",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Eleve.objects.count(), 0)
        self.assertContains(response, "champ(s) invalide(s)")

    def test_sans_authentification_redirection_login(self):
        self.client.logout()
        url = reverse("academics:eleve_bulk_create", args=[self.classe.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
