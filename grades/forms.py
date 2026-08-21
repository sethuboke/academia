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


NoteFormSet = formset_factory(NoteEntryForm, extra=0)