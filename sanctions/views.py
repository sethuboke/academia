from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from academics.models import Classe

from .forms import SanctionForm
from .models import Sanction


class SanctionListCreateView(LoginRequiredMixin, View):
    """Historique des sanctions d'une classe + formulaire d'ajout sur la même page."""
    template_name = "sanctions/sanction_list.html"

    def get(self, request, classe_pk):
        classe = get_object_or_404(Classe, pk=classe_pk)
        form = SanctionForm(classe=classe)
        sanctions = Sanction.objects.filter(eleve__classe=classe).select_related("eleve")
        return render(request, self.template_name, {
            "classe": classe, "form": form, "sanctions": sanctions,
        })

    def post(self, request, classe_pk):
        classe = get_object_or_404(Classe, pk=classe_pk)
        form = SanctionForm(request.POST, classe=classe)
        if form.is_valid():
            form.save()
            return redirect("sanctions:sanction_list", classe_pk=classe.pk)
        sanctions = Sanction.objects.filter(eleve__classe=classe).select_related("eleve")
        return render(request, self.template_name, {
            "classe": classe, "form": form, "sanctions": sanctions,
        })


class SanctionDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        sanction = get_object_or_404(Sanction, pk=pk)
        classe_pk = sanction.eleve.classe_id
        sanction.delete()
        return redirect("sanctions:sanction_list", classe_pk=classe_pk)