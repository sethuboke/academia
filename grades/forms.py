from django import forms
from django.forms import formset_factory


class NoteEntryForm(forms.Form):
    """
    Une ligne = un élève. eleve_id/eleve_nom sont préremplis côté vue à
    partir de la liste des élèves de la classe ; seul 'note' est modifié
    par l'utilisateur. Une note laissée vide n'est simplement pas
    enregistrée (l'élève n'a pas encore été interrogé sur ce point).
    """
    eleve_id = forms.IntegerField(widget=forms.HiddenInput)
    eleve_nom = forms.CharField(disabled=True, required=False, label="Élève")
    note = forms.DecimalField(
        max_digits=4, decimal_places=2, required=False,
        min_value=0, max_value=20, label="Note / 20",
    )


class InterrogationGrilleForm(forms.Form):
    """
    Une ligne = un élève, 4 colonnes de notes (I1 à I4).

    Chaque case préremplie avec l'interrogation existante (ordonnée par
    date de saisie) ; une case vidée supprime la note correspondante,
    une case modifiée met à jour la note, une case remplie crée une note.
    Les notes compactées (cases vides ignorées) sont réconciliées par
    position : vider une case du milieu décale les suivantes.
    """
    eleve_id = forms.IntegerField(widget=forms.HiddenInput)
    eleve_nom = forms.CharField(disabled=True, required=False, label="Élève")
    note_1 = forms.DecimalField(
        max_digits=4, decimal_places=2, required=False,
        min_value=0, max_value=20, label="I1",
    )
    note_2 = forms.DecimalField(
        max_digits=4, decimal_places=2, required=False,
        min_value=0, max_value=20, label="I2",
    )
    note_3 = forms.DecimalField(
        max_digits=4, decimal_places=2, required=False,
        min_value=0, max_value=20, label="I3",
    )
    note_4 = forms.DecimalField(
        max_digits=4, decimal_places=2, required=False,
        min_value=0, max_value=20, label="I4",
    )


class DevoirGrilleForm(forms.Form):
    """
    Une ligne = un élève, 2 colonnes fixes (D1, D2 par numéro de devoir).

    Une case vidée supprime le devoir correspondant, une case modifiée
    le met à jour, une case remplie le crée.
    """
    eleve_id = forms.IntegerField(widget=forms.HiddenInput)
    eleve_nom = forms.CharField(disabled=True, required=False, label="Élève")
    devoir_1 = forms.DecimalField(
        max_digits=4, decimal_places=2, required=False,
        min_value=0, max_value=20, label="D1",
    )
    devoir_2 = forms.DecimalField(
        max_digits=4, decimal_places=2, required=False,
        min_value=0, max_value=20, label="D2",
    )


NoteFormSet = formset_factory(NoteEntryForm, extra=0)
InterrogationGrilleFormSet = formset_factory(InterrogationGrilleForm, extra=0)
DevoirGrilleFormSet = formset_factory(DevoirGrilleForm, extra=0)