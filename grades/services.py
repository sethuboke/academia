"""
Moteur de calcul des moyennes (CDC §5.3).

Ces fonctions sont volontairement "pures" : elles ne touchent pas à l'ORM
Django, ne font aucune requête, et ne dépendent que de leurs arguments.
Elles peuvent donc être testées unitairement sans base de données, et
réutilisées aussi bien dans les vues, l'API IA, que dans des scripts
d'export.

La récupération des notes depuis la base (Interrogation, Devoir) est
gérée séparément, dans aggregations.py, qui appelle ces fonctions.
"""
from decimal import Decimal, ROUND_DOWN
from typing import Optional, Sequence, Tuple

TWO_PLACES = Decimal("0.01")
MAX_INTERROS = 4
MAX_DEVOIRS = 2


def _to_decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _round(value: Decimal) -> Decimal:
    # Troncature à 2 décimales (pas d'arrondi) : 13.336 -> 13.33, jamais 13.34.
    return value.quantize(TWO_PLACES, rounding=ROUND_DOWN)


def moyenne_interrogations(notes: Sequence) -> Optional[Decimal]:
    """
    Moy_I = (Interro_1 + ... + Interro_n) ÷ n, avec 1 ≤ n ≤ 4.

    Retourne None si aucune interrogation n'est encore saisie (pas
    d'erreur : c'est un état normal en cours de période).
    """
    notes = [_to_decimal(n) for n in notes]
    if not notes:
        return None
    if len(notes) > MAX_INTERROS:
        raise ValueError(f"Maximum {MAX_INTERROS} interrogations par matière et par semestre.")
    return _round(sum(notes) / len(notes))


def moyenne_matiere(moy_i: Optional[Decimal], devoirs: Sequence) -> Optional[Decimal]:
    """
    Moy_M = (Moy_I + Devoir_1 + Devoir_2) ÷ 3 dans le cas complet.

    Décision produit : si certains éléments manquent (pas encore
    d'interro, ou un seul des deux devoirs saisi), on calcule une
    moyenne PARTIELLE en divisant par le nombre réel d'éléments
    disponibles plutôt que d'attendre que tout soit saisi.

    Retourne None si strictement rien n'est saisi (ni Moy_I, ni devoir).
    """
    devoirs = [_to_decimal(d) for d in devoirs]
    if len(devoirs) > MAX_DEVOIRS:
        raise ValueError(f"Maximum {MAX_DEVOIRS} devoirs par matière et par semestre.")

    elements = []
    if moy_i is not None:
        elements.append(_to_decimal(moy_i))
    elements.extend(devoirs)

    if not elements:
        return None
    return _round(sum(elements) / len(elements))


def moyenne_matiere_coefficiee(moy_m: Optional[Decimal], coefficient) -> Optional[Decimal]:
    """Moy_Mc = Moy_M × Coefficient_matière. None si Moy_M est None."""
    if moy_m is None:
        return None
    return _round(_to_decimal(moy_m) * _to_decimal(coefficient))


def moyenne_semestre(moyennes_par_matiere: Sequence[Tuple[Optional[Decimal], int]]) -> Optional[Decimal]:
    """
    Moyenne générale d'un semestre, pondérée par les coefficients des
    matières. Formule non énoncée littéralement dans le CDC, mais
    cohérente avec Moy_Mc = Moy_M × coefficient :

        Moy_Semestre = Σ(Moy_Mc) ÷ Σ(coefficients)

    moyennes_par_matiere : séquence de tuples (Moy_Mc, coefficient),
    une entrée par matière de la classe. Les matières sans note saisie
    (Moy_Mc = None) sont exclues du calcul (ni note, ni coefficient
    comptés) plutôt que traitées comme un 0.
    """
    pertinents = [(mc, coef) for mc, coef in moyennes_par_matiere if mc is not None]
    if not pertinents:
        return None
    total_mc = sum(_to_decimal(mc) for mc, _ in pertinents)
    total_coef = sum(_to_decimal(coef) for _, coef in pertinents)
    if total_coef == 0:
        return None
    return _round(total_mc / total_coef)


def moyenne_annuelle(moy_s1: Optional[Decimal], moy_s2: Optional[Decimal]) -> Optional[Decimal]:
    """
    Moy_Annuelle = (Moy_S1 + 2 × Moy_S2) ÷ 3 — système public à 2 semestres.

    Si un des deux semestres n'a aucune moyenne calculable, la moyenne
    annuelle officielle ne peut pas être établie -> None plutôt qu'un
    résultat trompeur basé sur un seul semestre.
    """
    if moy_s1 is None or moy_s2 is None:
        return None
    return _round((_to_decimal(moy_s1) + 2 * _to_decimal(moy_s2)) / 3)