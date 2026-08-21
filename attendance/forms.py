from django import forms

from .models import Absence

FIELD_CLASSES = "w-full px-4 py-2.5 rounded-xl border border-blue-bell-200 bg-white text-blue-bell-900 placeholder-blue-bell-400 focus:outline-none focus:ring-2 focus:ring-blue-bell-500 focus:border-transparent transition text-sm"
SELECT_CLASSES = FIELD_CLASSES + " appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2024%2024%22%20stroke%3D%22%230f3757%22%20stroke-width%3D%222%22%3E%3Cpath%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20d%3D%22M19%209l-7%207-7-7%22%2F%3E%3C%2Fsvg%3E')] bg-no-repeat bg-[right_0.75rem_center] bg-[length:1rem] pr-10 cursor-pointer"


class AbsenceForm(forms.ModelForm):
    class Meta:
        model = Absence
        fields = ["eleve", "date", "type", "motif"]
        widgets = {
            "eleve": forms.Select(attrs={"class": SELECT_CLASSES}),
            "date": forms.DateInput(attrs={"class": FIELD_CLASSES, "type": "date"}),
            "type": forms.Select(attrs={"class": SELECT_CLASSES}),
            "motif": forms.TextInput(attrs={
                "class": FIELD_CLASSES,
                "placeholder": "Motif (optionnel)",
            }),
        }

    def __init__(self, *args, classe=None, **kwargs):
        super().__init__(*args, **kwargs)
        if classe is not None:
            self.fields["eleve"].queryset = classe.eleves.all()