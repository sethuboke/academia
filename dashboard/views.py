from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from academics.models import AnneeScolaire, Classe, Eleve, Matiere, Semestre
from attendance.models import Absence
from grades.models import Devoir, Interrogation


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
        classes = Classe.objects.select_related("annee_scolaire").prefetch_related("eleves")

        ctx.update({
            "annee_courante": annee_courante,
            "total_classes": classes.count(),
            "total_eleves": Eleve.objects.count(),
            "total_matieres": Matiere.objects.count(),
            "total_semestres": Semestre.objects.count(),
            "total_interrogations": Interrogation.objects.count(),
            "total_devoirs": Devoir.objects.count(),
            "total_absences": Absence.objects.count(),
            "classes": classes[:6],
        })
        return ctx