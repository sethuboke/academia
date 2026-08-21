from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from academics.models import Classe

from .forms import AbsenceForm
from .models import Absence


class AbsenceListCreateView(LoginRequiredMixin, View):
    """Historique des absences d'une classe + formulaire d'ajout sur la même page."""
    template_name = "attendance/absence_list.html"

    def get(self, request, classe_pk):
        classe = get_object_or_404(Classe, pk=classe_pk)
        form = AbsenceForm(classe=classe)
        absences = Absence.objects.filter(eleve__classe=classe).select_related("eleve")
        return render(request, self.template_name, {
            "classe": classe, "form": form, "absences": absences,
        })

    def post(self, request, classe_pk):
        classe = get_object_or_404(Classe, pk=classe_pk)
        form = AbsenceForm(request.POST, classe=classe)
        if form.is_valid():
            form.save()
            return redirect("attendance:absence_list", classe_pk=classe.pk)
        absences = Absence.objects.filter(eleve__classe=classe).select_related("eleve")
        return render(request, self.template_name, {
            "classe": classe, "form": form, "absences": absences,
        })


class AbsenceDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        absence = get_object_or_404(Absence, pk=pk)
        classe_pk = absence.eleve.classe_id
        absence.delete()
        return redirect("attendance:absence_list", classe_pk=classe_pk)