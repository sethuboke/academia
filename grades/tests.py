from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from academics.models import AnneeScolaire, Classe, ClasseMatiere, Eleve, Matiere, Semestre
from grades import aggregations
from grades.models import Conduite, Devoir, Interrogation


class ConduiteBaseTestCase(TestCase):
    """Jeu de données commun : une classe avec 1 matière (coef 2) et 2 élèves."""

    @classmethod
    def setUpTestData(cls):
        cls.annee = AnneeScolaire.objects.create(libelle="2025-2026", est_courante=True)
        cls.semestre = Semestre.objects.create(annee_scolaire=cls.annee, libelle="S1")
        cls.classe = Classe.objects.create(annee_scolaire=cls.annee, nom="Terminale D")
        cls.matiere = Matiere.objects.create(nom="Mathématiques")
        cls.classe_matiere = ClasseMatiere.objects.create(
            classe=cls.classe, matiere=cls.matiere, coefficient=2
        )
        cls.eleve1 = Eleve.objects.create(
            classe=cls.classe, nom="Ala", prenom="Premier", statut="N", genre="M",
        )
        cls.eleve2 = Eleve.objects.create(
            classe=cls.classe, nom="Bla", prenom="Second", statut="R", genre="F",
        )

    def noter(self, eleve, semestre=None):
        # Notes créées déjà validées : moy_semestre_eleve() filtre
        # sur valide=True par défaut.
        semestre = semestre or self.semestre
        Interrogation.objects.create(
            eleve=eleve, classe_matiere=self.classe_matiere, semestre=semestre,
            note=10, valide=True,
        )
        Devoir.objects.update_or_create(
            eleve=eleve, classe_matiere=self.classe_matiere, semestre=semestre,
            numero=1, defaults={"note": 15, "valide": True},
        )


class ConduiteModelTests(ConduiteBaseTestCase):
    def test_une_seule_conduite_par_eleve_et_semestre(self):
        Conduite.objects.create(eleve=self.eleve1, semestre=self.semestre, note=14)
        with self.assertRaises(ValidationError):
            # full_clean() dans save() doit lever l'erreur d'unicité.
            Conduite(eleve=self.eleve1, semestre=self.semestre, note=15).save()

    def test_note_hors_bornes_refusee(self):
        with self.assertRaises(ValidationError):
            Conduite.objects.create(eleve=self.eleve1, semestre=self.semestre, note=25)
        with self.assertRaises(ValidationError):
            Conduite.objects.create(eleve=self.eleve2, semestre=self.semestre, note=-1)

    def test_semestre_d_autre_annee_refuse(self):
        annee2 = AnneeScolaire.objects.create(libelle="2024-2025")
        autre_semestre = Semestre.objects.create(annee_scolaire=annee2, libelle="S2")
        with self.assertRaises(ValidationError):
            Conduite.objects.create(eleve=self.eleve1, semestre=autre_semestre, note=14)

    def test_horodatage_validation(self):
        conduite = Conduite(valide=True, eleve=self.eleve1, semestre=self.semestre, note=14)
        conduite.save()
        self.assertIsNotNone(conduite.date_validation)

    def test_resaisie_met_a_jour_sans_dupliquer(self):
        Conduite.objects.create(eleve=self.eleve1, semestre=self.semestre, note=10)
        Conduite.objects.update_or_create(
            eleve=self.eleve1, semestre=self.semestre, defaults={"note": 16},
        )
        self.assertEqual(Conduite.objects.filter(eleve=self.eleve1).count(), 1)
        self.assertEqual(Conduite.objects.get(eleve=self.eleve1).note, Decimal("16"))


class MoyenneSemestreAvecConduiteTests(ConduiteBaseTestCase):
    """
    Moy_M élève = (Moy_I + Devoir) / 2 ; ici : (10 + 15) / 2 = 12.50
    Moy_Mc = 12.50 x coef 2 = 25.00
    Sans conduite : Moy_Semestre = 25 / 2 = 12.50
    Avec conduite c (coef 1)   : Moy_Semestre = (25 + c) / 3
    """

    def test_sans_conduite_le_calcul_est_inchange(self):
        self.noter(self.eleve1)
        self.assertEqual(
            aggregations.moy_semestre_eleve(self.eleve1, self.semestre),
            Decimal("12.50"),
        )

    def test_conduite_validee_entree_en_compte_coef_1(self):
        self.noter(self.eleve1)
        Conduite.objects.create(eleve=self.eleve1, semestre=self.semestre, note=18, valide=True)
        # (25 + 18) / 3 = 14.333... -> tronqué à 14.33
        self.assertEqual(
            aggregations.moy_semestre_eleve(self.eleve1, self.semestre),
            Decimal("14.33"),
        )

    def test_conduite_non_validee_ignoree_par_defaut(self):
        self.noter(self.eleve1)
        Conduite.objects.create(eleve=self.eleve1, semestre=self.semestre, note=0)
        self.assertEqual(
            aggregations.moy_semestre_eleve(self.eleve1, self.semestre),
            Decimal("12.50"),
        )

    def test_conduite_non_validee_comptee_si_demande(self):
        self.noter(self.eleve1)
        Conduite.objects.create(eleve=self.eleve1, semestre=self.semestre, note=0)
        # (25 + 0) / 3 = 8.333... -> 8.33
        self.assertEqual(
            aggregations.moy_semestre_eleve(self.eleve1, self.semestre, seulement_validees=False),
            Decimal("8.33"),
        )

    def test_conduite_seule_sans_notes_matieres(self):
        """La conduite seule suffit à produire une moyenne semestrielle."""
        Conduite.objects.create(eleve=self.eleve2, semestre=self.semestre, note=15, valide=True)
        self.assertEqual(
            aggregations.moy_semestre_eleve(self.eleve2, self.semestre),
            Decimal("15.00"),
        )

    def test_moyenne_annuelle_inclut_la_conduite_via_les_semestres(self):
        semestre2 = Semestre.objects.create(annee_scolaire=self.annee, libelle="S2")
        self.noter(self.eleve1)
        Conduite.objects.create(eleve=self.eleve1, semestre=self.semestre, note=18, valide=True)
        Conduite.objects.create(eleve=self.eleve1, semestre=semestre2, note=9, valide=True)
        # S1 = (25+18)/3 = 14.33 ; S2 = 9.00 ; Annuelle = (14.33 + 18) / 3 = 10.776 -> 10.77
        self.assertEqual(
            aggregations.moy_annuelle_eleve(self.eleve1, self.semestre, semestre2),
            Decimal("10.77"),
        )


class SaisieConduiteViewTests(ConduiteBaseTestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.client.force_login(User.objects.create_user("prof", password="x"))

    def test_get_affiche_une_ligne_par_eleve(self):
        resp = self.client.get(reverse("grades:saisie_conduite", args=[self.classe.pk, self.semestre.pk]))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn(str(self.eleve1), content)
        self.assertIn(str(self.eleve2), content)

    def test_post_enregistre_et_puis_met_a_jour(self):
        url = reverse("grades:saisie_conduite", args=[self.classe.pk, self.semestre.pk])
        data = {
            "form-TOTAL_FORMS": "2",
            "form-INITIAL_FORMS": "2",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-eleve_id": str(self.eleve1.pk),
            "form-0-note": "17",
            "form-1-eleve_id": str(self.eleve2.pk),
            "form-1-note": "",
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Conduite.objects.count(), 1)
        self.assertEqual(Conduite.objects.get(eleve=self.eleve1).note, Decimal("17"))

        # Nouvelle saisie pour le même élève : mise à jour, pas de doublon.
        data["form-0-note"] = "12"
        self.client.post(url, data)
        self.assertEqual(Conduite.objects.filter(eleve=self.eleve1).count(), 1)
        self.assertEqual(Conduite.objects.get(eleve=self.eleve1).note, Decimal("12"))

    def test_acces_requiert_authentification(self):
        self.client.logout()
        resp = self.client.get(reverse("grades:saisie_conduite", args=[self.classe.pk, self.semestre.pk]))
        self.assertEqual(resp.status_code, 302)

    def test_bandeau_validation_affiche_nb_a_valider(self):
        Conduite.objects.create(eleve=self.eleve1, semestre=self.semestre, note=14)
        url = reverse("grades:saisie_conduite", args=[self.classe.pk, self.semestre.pk])
        content = self.client.get(url).content.decode()
        self.assertIn("1 conduite(s) non validée(s)", content)


class ValiderConduitesViewTests(ConduiteBaseTestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.client.force_login(User.objects.create_user("directeur", password="x"))

    def test_post_valide_toutes_les_conduites_du_semestre(self):
        c1 = Conduite.objects.create(eleve=self.eleve1, semestre=self.semestre, note=18)
        c2 = Conduite.objects.create(eleve=self.eleve2, semestre=self.semestre, note=10)
        resp = self.client.post(reverse("grades:valider_conduites", args=[self.classe.pk, self.semestre.pk]))
        self.assertEqual(resp.status_code, 302)
        c1.refresh_from_db()
        c2.refresh_from_db()
        self.assertTrue(c1.valide)
        self.assertIsNotNone(c1.date_validation)
        self.assertTrue(c2.valide)

    def test_conduite_validee_devient_visible_dans_la_moyenne(self):
        """Scénario complet : saisie -> validation -> entrée en compte (coef 1)."""
        self.noter(self.eleve1)
        Conduite.objects.create(eleve=self.eleve1, semestre=self.semestre, note=18)
        # Avant validation : conduite ignorée -> 12.50
        self.assertEqual(
            aggregations.moy_semestre_eleve(self.eleve1, self.semestre),
            Decimal("12.50"),
        )
        self.client.post(reverse("grades:valider_conduites", args=[self.classe.pk, self.semestre.pk]))
        # Après validation : (25 + 18) / 3 = 14.33
        self.assertEqual(
            aggregations.moy_semestre_eleve(self.eleve1, self.semestre),
            Decimal("14.33"),
        )


class StatutReleveTests(ConduiteBaseTestCase):
    """
    Le statut d'une ligne du relevé vaut "Complet" uniquement lorsque
    2 interrogations ET les 2 devoirs sont saisis.
    """

    def _lignes(self):
        from django.contrib.auth.models import User

        client = self.client
        client.force_login(User.objects.create_user("prof_statut", password="x"))
        resp = client.get(reverse(
            "grades:releve_notes", args=[self.classe_matiere.pk, self.semestre.pk]
        ))
        self.assertEqual(resp.status_code, 200)
        return {l["eleve"].pk: l for l in resp.context["lignes"]}

    def test_aucune_note(self):
        lignes = self._lignes()
        ligne = lignes[self.eleve1.pk]
        self.assertFalse(ligne["a_des_notes"])
        self.assertFalse(ligne["complet"])

    def test_partiel_avec_une_interro_et_un_devoir(self):
        Interrogation.objects.create(
            eleve=self.eleve1, classe_matiere=self.classe_matiere, semestre=self.semestre, note=10
        )
        Devoir.objects.update_or_create(
            eleve=self.eleve1, classe_matiere=self.classe_matiere, semestre=self.semestre,
            numero=1, defaults={"note": 15},
        )
        ligne = self._lignes()[self.eleve1.pk]
        self.assertTrue(ligne["a_des_notes"])
        self.assertFalse(ligne["complet"])

    def test_complet_avec_2_interros_et_2_devoirs(self):
        for note in (10, 12):
            Interrogation.objects.create(
                eleve=self.eleve1, classe_matiere=self.classe_matiere,
                semestre=self.semestre, note=note,
            )
        Devoir.objects.update_or_create(
            eleve=self.eleve1, classe_matiere=self.classe_matiere, semestre=self.semestre,
            numero=1, defaults={"note": 15},
        )
        Devoir.objects.update_or_create(
            eleve=self.eleve1, classe_matiere=self.classe_matiere, semestre=self.semestre,
            numero=2, defaults={"note": 14},
        )
        ligne = self._lignes()[self.eleve1.pk]
        self.assertTrue(ligne["complet"])

    def test_non_complet_si_un_devoir_manquant(self):
        for note in (10, 12):
            Interrogation.objects.create(
                eleve=self.eleve1, classe_matiere=self.classe_matiere,
                semestre=self.semestre, note=note,
            )
        Devoir.objects.update_or_create(
            eleve=self.eleve1, classe_matiere=self.classe_matiere, semestre=self.semestre,
            numero=1, defaults={"note": 15},
        )
        ligne = self._lignes()[self.eleve1.pk]
        self.assertFalse(ligne["complet"])

class CalculerRangsTests(TestCase):
    """Logique pure du classement, y compris les ex æquo."""

    def test_ex_aquo_partagent_le_meme_rang_avec_saut(self):
        # 14, 13, 13, 12 -> rangs 1, 2, 2, 4 (classement compétition)
        rangs = aggregations.calculer_rangs([
            ("a", Decimal("14.00")),
            ("b", Decimal("13.00")),
            ("c", Decimal("13.00")),
            ("d", Decimal("12.00")),
        ])
        self.assertEqual(rangs, {"a": 1, "b": 2, "c": 2, "d": 4})

    def test_eleve_sans_moyenne_non_classe(self):
        # Un élève sans moyenne calculable n'est ni classé ni compté.
        rangs = aggregations.calculer_rangs([
            ("a", Decimal("14.00")),
            ("b", None),
        ])
        self.assertEqual(rangs, {"a": 1})

    def test_tous_ex_aquo_premier_rang_partage(self):
        rangs = aggregations.calculer_rangs([
            ("a", Decimal("10.00")),
            ("b", Decimal("10.00")),
            ("c", Decimal("10.00")),
        ])
        self.assertEqual(rangs, {"a": 1, "b": 1, "c": 1})


class RangsSemestrielsEtAnnuelsTests(ConduiteBaseTestCase):
    """
    Rangs sur données réelles. Avec 1 matière coef 2 et moyenne matière
    12.50 (Moy_Mc = 25) :
        Moy_Semestre = (25 + conduite) / 3   si conduite validée,
                     = 12.50                 sinon.
    """

    def _conduite(self, eleve, note):
        Conduite.objects.create(
            eleve=eleve, semestre=self.semestre, note=note, valide=True
        )

    def test_ex_aquo_en_semestre_et_non_note_non_classe(self):
        self.noter(self.eleve1)
        eleve3 = Eleve.objects.create(classe=self.classe, nom="Cla", prenom="Troisieme", statut="N", genre="M")
        eleve4 = Eleve.objects.create(classe=self.classe, nom="Dla", prenom="Quatrieme", statut="R", genre="F")
        self._conduite(self.eleve1, 15)          # (25 + 15) / 3 = 13.33 -> 1er
        self._conduite(eleve3, 12)               # (25 + 12) / 3 = 12.33 -> ex æquo 2e
        self._conduite(eleve4, 12)               # idem
        # eleve2 : aucune note validée -> non classé.

        rangs = aggregations.rangs_semestriels_classe(self.classe, self.semestre)
        self.assertEqual(rangs[self.eleve1.pk], 1)
        self.assertEqual(rangs[eleve3.pk], 2)
        self.assertEqual(rangs[eleve4.pk], 2)    # ex æquo : même rang
        self.assertNotIn(self.eleve2.pk, rangs)

    def test_notes_non_validees_ignorees_pour_le_classement(self):
        # eleve1 a des notes mais NON validées ; eleve2 non plus.
        Interrogation.objects.create(
            eleve=self.eleve1, classe_matiere=self.classe_matiere,
            semestre=self.semestre, note=18,
        )
        rangs = aggregations.rangs_semestriels_classe(self.classe, self.semestre)
        self.assertEqual(rangs, {})

    def test_rang_annuel_avec_ex_aquo(self):
        semestre2 = Semestre.objects.create(annee_scolaire=self.annee, libelle="S2")
        eleve3 = Eleve.objects.create(classe=self.classe, nom="Cla", prenom="Troisieme", statut="N", genre="M")
        eleve4 = Eleve.objects.create(classe=self.classe, nom="Dla", prenom="Quatrieme", statut="R", genre="F")
        for sem in (self.semestre, semestre2):
            for e in (self.eleve1, self.eleve2):
                self.noter(e)
            Conduite.objects.create(
                eleve=self.eleve1, semestre=sem, note=15, valide=True,
            )
            Conduite.objects.create(
                eleve=self.eleve2, semestre=sem, note=10, valide=True,
            )
        # eleve3/eleve4 : notes S1 seulement, pas de S2 -> pas de moyenne
        # annuelle -> non classés en annuel.

        rangs = aggregations.rangs_annuels_classe(self.classe, self.semestre, semestre2)
        self.assertEqual(rangs[self.eleve1.pk], 1)
        self.assertEqual(rangs[self.eleve2.pk], 2)
        self.assertNotIn(eleve3.pk, rangs)
        self.assertNotIn(eleve4.pk, rangs)

