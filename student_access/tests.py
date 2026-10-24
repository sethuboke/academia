from django.test import TestCase
from django.urls import reverse

from grades.models import Conduite, Devoir, Interrogation
from grades.tests import ConduiteBaseTestCase


class ConsultationConduiteTests(ConduiteBaseTestCase):
    """La conduite validée doit apparaître sur la page de consultation élève."""

    def test_conduite_validee_affichee_avec_sa_moyenne_integree(self):
        self.noter(self.eleve1)
        Conduite.objects.create(eleve=self.eleve1, semestre=self.semestre, note=18, valide=True)
        resp = self.client.post(
            reverse("student_access:consulter", args=[self.classe.lien_public_uid]),
            {"nom": "Ala", "prenom": "Premier"},
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn("Conduite", content)
        # Moyenne semestre = (25 + 18) / 3 = 14,33 (format localisé fr),
        # conduite incluse
        self.assertIn("14,33", content)

    def test_conduite_non_validee_non_affichee(self):
        self.noter(self.eleve1)
        Conduite.objects.create(eleve=self.eleve1, semestre=self.semestre, note=18)
        resp = self.client.post(
            reverse("student_access:consulter", args=[self.classe.lien_public_uid]),
            {"nom": "Ala", "prenom": "Premier"},
        )
        content = resp.content.decode()
        # La ligne "Conduite" du tableau ne doit pas apparaître.
        self.assertNotIn(">Conduite</td>", content)
        # Et la moyenne ne doit PAS inclure la conduite : 12,50 (pas 14,33).
        self.assertIn("12,50", content)
        self.assertNotIn("14,33", content)


class ConsultationRangTests(ConduiteBaseTestCase):
    """Le rang (semestriel et annuel) doit être visible sur la page de
    consultation élève, avec gestion des ex æquo."""

    def _post_consultation(self):
        return self.client.post(
            reverse("student_access:consulter", args=[self.classe.lien_public_uid]),
            {"nom": "Ala", "prenom": "Premier"},
        )

    def test_rang_semestriel_affiche(self):
        # eleve1 et eleve2 ont les mêmes notes -> ex æquo 1ers sur 2 classés.
        self.noter(self.eleve1)
        self.noter(self.eleve2)
        resp = self._post_consultation()
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        # Même présentation que le bilan interne : rang / effectif classé.
        self.assertIn("1<span class=\"text-sm font-normal text-blue-bell-400\">/2", content)
        self.assertNotIn("/3</span>", content)

    def test_rang_annuel_affiche_si_deux_semestres_notes(self):
        from academics.models import Semestre

        semestre2 = Semestre.objects.create(annee_scolaire=self.annee, libelle="S2")
        for e in (self.eleve1, self.eleve2):
            # Les deux semestres doivent être notés pour que la moyenne
            # annuelle (et donc le rang annuel) soit calculable.
            self.noter(e)
            self.noter(e, semestre=semestre2)
        resp = self._post_consultation()
        content = resp.content.decode()
        # Même présentation que le bilan interne : rang / effectif classé.
        self.assertIn("1<span class=\"text-sm font-normal text-blue-bell-400\">/2", content)

    def test_pas_de_rang_sans_moyenne_validee(self):
        # Aucune note validée : pas de moyenne, donc pas de rang affiché.
        Interrogation.objects.create(
            eleve=self.eleve1, classe_matiere=self.classe_matiere,
            semestre=self.semestre, note=15,
        )
        resp = self._post_consultation()
        content = resp.content.decode()
        self.assertNotIn("<sup>e</sup>", content)


class ConsultationBilanPartageTests(ConduiteBaseTestCase):
    def test_lien_public_est_court_et_garde_l_ancien_lien_actif(self):
        url = reverse("student_access:consulter", args=[self.classe.lien_public_uid])
        self.assertTrue(url.startswith("/notes/"))
        self.assertEqual(len(url.strip("/").split("/")[-1]), 22)

        ancienne_url = reverse(
            "student_access:consulter_legacy", args=[self.classe.lien_public_uid]
        )
        self.assertEqual(self.client.get(ancienne_url).status_code, 200)

    def test_consultation_utilise_le_bilan_et_ne_montre_que_les_notes_validees(self):
        Interrogation.objects.create(
            eleve=self.eleve1, classe_matiere=self.classe_matiere,
            semestre=self.semestre, note=7.25, valide=True,
        )
        Interrogation.objects.create(
            eleve=self.eleve1, classe_matiere=self.classe_matiere,
            semestre=self.semestre, note=19.25, valide=False,
        )
        Devoir.objects.create(
            eleve=self.eleve1, classe_matiere=self.classe_matiere,
            semestre=self.semestre, numero=1, note=16.25, valide=True,
        )

        response = self.client.post(
            reverse("student_access:consulter", args=[self.classe.lien_public_uid]),
            {"nom": self.eleve1.nom, "prenom": self.eleve1.prenom},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "grades/bilan_eleve.html")
        self.assertContains(response, "I1")
        self.assertContains(response, "D1")
        self.assertContains(response, "7,25")
        self.assertContains(response, "16,25")
        self.assertNotContains(response, "19,25")
        self.assertNotContains(response, "Saisir les notes")

# Create your tests here.

