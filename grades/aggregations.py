"""
Pont entre l'ORM Django (Interrogation, Devoir, ClasseMatiere) et le
moteur de calcul pur (services.py). Toute la logique de requêtage vit
ici ; services.py reste sans dépendance Django.
"""
from grades.models import Interrogation, Devoir
from grades import services


def moy_i_eleve_matiere_semestre(eleve, classe_matiere, semestre, seulement_validees=True):
    """Calcule Moy_I pour un élève, une matière (de classe) et un semestre donnés."""
    qs = Interrogation.objects.filter(
        eleve=eleve, classe_matiere=classe_matiere, semestre=semestre
    )
    if seulement_validees:
        qs = qs.filter(valide=True)
    notes = list(qs.values_list("note", flat=True))
    return services.moyenne_interrogations(notes)


def moy_m_eleve_matiere_semestre(eleve, classe_matiere, semestre, seulement_validees=True):
    """Calcule Moy_M (moyenne matière, avant coefficient) pour un élève/semestre."""
    moy_i = moy_i_eleve_matiere_semestre(eleve, classe_matiere, semestre, seulement_validees)

    qs = Devoir.objects.filter(
        eleve=eleve, classe_matiere=classe_matiere, semestre=semestre
    )
    if seulement_validees:
        qs = qs.filter(valide=True)
    devoirs = list(qs.values_list("note", flat=True))

    return services.moyenne_matiere(moy_i, devoirs)


def moy_mc_eleve_matiere_semestre(eleve, classe_matiere, semestre, seulement_validees=True):
    """Calcule Moy_Mc (moyenne matière coefficiée) pour un élève/semestre."""
    moy_m = moy_m_eleve_matiere_semestre(eleve, classe_matiere, semestre, seulement_validees)
    return services.moyenne_matiere_coefficiee(moy_m, classe_matiere.coefficient)


def moy_semestre_eleve(eleve, semestre, seulement_validees=True):
    """
    Moyenne générale d'un élève pour un semestre donné, toutes matières
    de sa classe confondues, pondérée par les coefficients.
    """
    classe_matieres = eleve.classe.classe_matieres.all()
    paires = []
    for cm in classe_matieres:
        moy_mc = moy_mc_eleve_matiere_semestre(eleve, cm, semestre, seulement_validees)
        paires.append((moy_mc, cm.coefficient))
    return services.moyenne_semestre(paires)


def moy_annuelle_eleve(eleve, semestre_s1, semestre_s2, seulement_validees=True):
    """Moyenne annuelle d'un élève à partir des deux semestres de l'année scolaire."""
    moy_s1 = moy_semestre_eleve(eleve, semestre_s1, seulement_validees)
    moy_s2 = moy_semestre_eleve(eleve, semestre_s2, seulement_validees)
    return services.moyenne_annuelle(moy_s1, moy_s2)