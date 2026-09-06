"""
Pont entre l'ORM Django (Interrogation, Devoir, ClasseMatiere) et le
moteur de calcul pur (services.py). Toute la logique de requêtage vit
ici ; services.py reste sans dépendance Django.
"""
from grades.models import Conduite, Interrogation, Devoir
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

    La conduite est incluse comme une "matière" de coefficient 1 : elle
    n'a ni interrogation ni devoir, sa note joue directement le rôle de
    la moyenne coefficiée (Moy_Mc). Elle est exclue du calcul si aucune
    conduite n'est saisie (ou non validée selon le filtre), jamais
    traitée comme un 0.
    """
    classe_matieres = eleve.classe.classe_matieres.all()
    paires = []
    for cm in classe_matieres:
        moy_mc = moy_mc_eleve_matiere_semestre(eleve, cm, semestre, seulement_validees)
        paires.append((moy_mc, cm.coefficient))

    conduite_qs = Conduite.objects.filter(eleve=eleve, semestre=semestre)
    if seulement_validees:
        conduite_qs = conduite_qs.filter(valide=True)
    conduite = conduite_qs.first()
    if conduite is not None:
        paires.append((conduite.note, Conduite.COEFFICIENT))

    return services.moyenne_semestre(paires)


def moy_annuelle_eleve(eleve, semestre_s1, semestre_s2, seulement_validees=True):
    """Moyenne annuelle d'un élève à partir des deux semestres de l'année scolaire."""
    moy_s1 = moy_semestre_eleve(eleve, semestre_s1, seulement_validees)
    moy_s2 = moy_semestre_eleve(eleve, semestre_s2, seulement_validees)
    return services.moyenne_annuelle(moy_s1, moy_s2)


# ---------------------------------------------------------------------------
# Rangs (classement avec gestion des ex æquo)
# ---------------------------------------------------------------------------

def calculer_rangs(valeurs_par_eleve):
    """
    Calcule le rang de chaque élève à partir de sa moyenne.

    Classement « compétition » (celui utilisé dans les bulletins) :
    les ex æquo partagent le MÊME rang et la position suivante est
    sautée. Exemple avec les moyennes 14, 13, 13, 12 :

        rangs = 1, 2, 2, 4   (et non 1, 2, 2, 3 ni 1, 2, 3, 4)

    Les élèves sans moyenne calculable (None : aucune note validée)
    ne sont PAS classés et n'entrent pas dans l'effectif classé :
    un élève ne peut pas être « 5e sur 30 » si seuls 20 élèves ont
    des notes.

    Les moyennes comparées sont celles déjà tronquées à 2 décimales
    par services._round() : deux élèves affichant la même moyenne
    sur leur bulletin sont donc forcément ex æquo.

    valeurs_par_eleve : itérable de tuples (eleve_id, moyenne|None).
    Retourne un dict {eleve_id: rang} limité aux élèves classés.
    """
    classes = [(eid, moy) for eid, moy in valeurs_par_eleve if moy is not None]
    # Tri décroissant ; en cas d'égalité l'ordre entre ex æquo est
    # indifférent puisqu'ils reçoivent le même rang.
    classes.sort(key=lambda paire: paire[1], reverse=True)

    rangs = {}
    rang_courant = 0
    moyenne_precedente = None
    for position, (eleve_id, moyenne) in enumerate(classes, start=1):
        if moyenne_precedente is None or moyenne != moyenne_precedente:
            rang_courant = position
            moyenne_precedente = moyenne
        rangs[eleve_id] = rang_courant
    return rangs


def rangs_semestriels_classe(classe, semestre, seulement_validees=True):
    """
    Rangs de TOUS les élèves d'une classe pour un semestre donné,
    calculés uniquement sur les notes validées par défaut (même règle
    que l'affichage côté consultation élève).

    Retourne {eleve_id: rang} — les élèves sans moyenne validée sont absents.
    """
    valeurs = [
        (eleve.pk, moy_semestre_eleve(eleve, semestre, seulement_validees))
        for eleve in classe.eleves.all()
    ]
    return calculer_rangs(valeurs)


def rangs_annuels_classe(classe, semestre_s1, semestre_s2, seulement_validees=True):
    """
    Rangs de TOUS les élèves d'une classe sur la moyenne ANNUELLE
    (formule (S1 + 2×S2)/3). Un élève n'est classé que s'il possède
    une moyenne annuelle calculable, c'est-à-dire les DEUX moyennes
    semestrielles (voir services.moyenne_annuelle).
    """
    valeurs = [
        (eleve.pk, moy_annuelle_eleve(eleve, semestre_s1, semestre_s2, seulement_validees))
        for eleve in classe.eleves.all()
    ]
    return calculer_rangs(valeurs)