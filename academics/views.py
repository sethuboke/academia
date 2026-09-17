from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import (
    AnneeScolaireForm,
    ClasseForm,
    ClasseMatiereForm,
    EleveBulkFormSet,
    EleveForm,
    MatiereForm,
    SemestreForm,
)
from .models import AnneeScolaire, Classe, ClasseMatiere, Eleve, Matiere, Semestre


class AnneeScolaireListView(LoginRequiredMixin, ListView):
    model = AnneeScolaire
    template_name = "academics/anneescolaire_list.html"
    context_object_name = "annees"


class AnneeScolaireCreateView(LoginRequiredMixin, CreateView):
    model = AnneeScolaire
    form_class = AnneeScolaireForm
    template_name = "academics/anneescolaire_form.html"
    success_url = reverse_lazy("academics:anneescolaire_list")

    def form_valid(self, form):
        # Si cette année est marquée courante, désactiver les autres
        if form.cleaned_data.get("est_courante"):
            AnneeScolaire.objects.filter(est_courante=True).update(est_courante=False)
        messages.success(self.request, "Année scolaire créée avec succès.")
        return super().form_valid(form)


class AnneeScolaireUpdateView(LoginRequiredMixin, UpdateView):
    model = AnneeScolaire
    form_class = AnneeScolaireForm
    template_name = "academics/anneescolaire_form.html"
    success_url = reverse_lazy("academics:anneescolaire_list")

    def form_valid(self, form):
        if form.cleaned_data.get("est_courante"):
            AnneeScolaire.objects.filter(est_courante=True).exclude(pk=self.object.pk).update(est_courante=False)
        messages.success(self.request, "Année scolaire modifiée avec succès.")
        return super().form_valid(form)


class AnneeScolaireDeleteView(LoginRequiredMixin, DeleteView):
    model = AnneeScolaire
    template_name = "academics/anneescolaire_confirm_delete.html"
    success_url = reverse_lazy("academics:anneescolaire_list")


class SemestreListView(LoginRequiredMixin, ListView):
    model = Semestre
    template_name = "academics/semestre_list.html"
    context_object_name = "semestres"


class SemestreCreateView(LoginRequiredMixin, CreateView):
    model = Semestre
    form_class = SemestreForm
    template_name = "academics/semestre_form.html"
    success_url = reverse_lazy("academics:semestre_list")


class SemestreUpdateView(LoginRequiredMixin, UpdateView):
    model = Semestre
    form_class = SemestreForm
    template_name = "academics/semestre_form.html"
    success_url = reverse_lazy("academics:semestre_list")


class SemestreDeleteView(LoginRequiredMixin, DeleteView):
    model = Semestre
    template_name = "academics/semestre_confirm_delete.html"
    success_url = reverse_lazy("academics:semestre_list")


class MatiereListView(LoginRequiredMixin, ListView):
    model = Matiere
    template_name = "academics/matiere_list.html"
    context_object_name = "matieres"


class MatiereCreateView(LoginRequiredMixin, CreateView):
    model = Matiere
    form_class = MatiereForm
    template_name = "academics/matiere_form.html"
    success_url = reverse_lazy("academics:matiere_list")


class MatiereUpdateView(LoginRequiredMixin, UpdateView):
    model = Matiere
    form_class = MatiereForm
    template_name = "academics/matiere_form.html"
    success_url = reverse_lazy("academics:matiere_list")


class MatiereDeleteView(LoginRequiredMixin, DeleteView):
    model = Matiere
    template_name = "academics/matiere_confirm_delete.html"
    success_url = reverse_lazy("academics:matiere_list")


class ClasseListView(LoginRequiredMixin, ListView):
    model = Classe
    template_name = "academics/classe_list.html"
    context_object_name = "classes"

    def get_queryset(self):
        """
        Classes regroupées par année scolaire : l'année courante d'abord,
        puis les années passées de la plus récente à la plus ancienne ;
        dans chaque groupe, classes triées par nom.
        Cet ordre permet le regroupement par année directement dans le
        template ({% regroup %}).
        """
        return (
            Classe.objects.select_related("annee_scolaire")
            .order_by("-annee_scolaire__est_courante", "-annee_scolaire__libelle", "nom")
        )


class ClasseCreateView(LoginRequiredMixin, CreateView):
    model = Classe
    form_class = ClasseForm
    template_name = "academics/classe_form.html"
    success_url = reverse_lazy("academics:classe_list")


class ClasseUpdateView(LoginRequiredMixin, UpdateView):
    model = Classe
    form_class = ClasseForm
    template_name = "academics/classe_form.html"
    success_url = reverse_lazy("academics:classe_list")


class ClasseDeleteView(LoginRequiredMixin, DeleteView):
    model = Classe
    template_name = "academics/classe_confirm_delete.html"
    success_url = reverse_lazy("academics:classe_list")


class ClasseDetailView(LoginRequiredMixin, DetailView):
    """
    Vue centrale de la classe : liste des élèves et des matières affectées.
    Point d'entrée vers la saisie des absences et des notes pour cette classe.
    """
    model = Classe
    template_name = "academics/classe_detail.html"
    context_object_name = "classe"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        eleves = self.object.eleves.all()
        ctx["eleves"] = eleves
        # Effectifs par genre affichés avant l'effectif total sur la fiche classe.
        ctx["nb_filles"] = eleves.filter(genre=Eleve.Genre.FEMININ).count()
        ctx["nb_garcons"] = eleves.filter(genre=Eleve.Genre.MASCULIN).count()
        ctx["classe_matieres"] = self.object.classe_matieres.select_related("matiere")
        ctx["semestres"] = self.object.annee_scolaire.semestres.all()
        return ctx


class EleveCreateView(LoginRequiredMixin, CreateView):
    model = Eleve
    form_class = EleveForm
    template_name = "academics/eleve_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.classe = get_object_or_404(Classe, pk=kwargs["classe_pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.classe = self.classe
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("academics:classe_detail", args=[self.classe.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["classe"] = self.classe
        return ctx


class EleveUpdateView(LoginRequiredMixin, UpdateView):
    model = Eleve
    form_class = EleveForm
    template_name = "academics/eleve_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["classe"] = self.object.classe
        return ctx

    def get_success_url(self):
        return reverse("academics:classe_detail", args=[self.object.classe_id])


class EleveDeleteView(LoginRequiredMixin, DeleteView):
    model = Eleve
    template_name = "academics/eleve_confirm_delete.html"

    def get_success_url(self):
        return reverse("academics:classe_detail", args=[self.object.classe_id])


class EleveBulkCreateView(LoginRequiredMixin, View):
    """Enregistrement groupé de plusieurs apprenants pour une classe."""
    template_name = "academics/eleve_bulk_form.html"
    prefix = "eleves"

    def dispatch(self, request, *args, **kwargs):
        self.classe = get_object_or_404(Classe, pk=kwargs["classe_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Une ligne pré-remplie permet de comprendre la structure du formulaire.
        initial = [{"statut": Eleve.Statut.NOUVEAU, "genre": Eleve.Genre.MASCULIN}]
        formset = EleveBulkFormSet(prefix=self.prefix, initial=initial)
        return render(request, self.template_name, {
            "classe": self.classe, "formset": formset,
        })

    def post(self, request, *args, **kwargs):
        formset = EleveBulkFormSet(request.POST, prefix=self.prefix)

        # Validation ligne par ligne : une ligne entièrement vide est simplement
        # ignorée (l'utilisateur ne doit pas être bloqué par des lignes vides).
        crees = 0
        deja_existants = []
        invalides = []
        for form in formset:
            nom_brut = form.data.get(form.add_prefix("nom"), "") or ""
            prenom_brut = form.data.get(form.add_prefix("prenom"), "") or ""
            if not nom_brut.strip() and not prenom_brut.strip():
                continue  # ligne vide : rien à enregistrer
            if not form.is_valid():
                nom_affiche = nom_brut.strip() or prenom_brut.strip() or "Ligne"
                invalides.append(nom_affiche)
                continue
            # Le formulaire a déjà normalisé la casse (nom en majuscules,
            # prénom avec majuscule initiale).
            nom = form.cleaned_data["nom"]
            prenom = form.cleaned_data["prenom"]
            # Unicité (classe, nom, prénom) : ne pas dupliquer un apprenant
            # existant, même si l'ancienne saisie n'était pas normalisée.
            if Eleve.objects.filter(
                classe=self.classe, nom__iexact=nom, prenom__iexact=prenom
            ).exists():
                deja_existants.append(f"{nom} {prenom}")
                continue
            Eleve.objects.create(
                classe=self.classe,
                nom=nom,
                prenom=prenom,
                genre=form.cleaned_data["genre"],
                statut=form.cleaned_data["statut"],
            )
            crees += 1

        if invalides:
            for nom_affiche in invalides:
                messages.error(self.request, f"Ligne « {nom_affiche} » : champ(s) invalide(s).")
            return render(request, self.template_name, {
                "classe": self.classe, "formset": formset,
            })

        if crees:
            messages.success(self.request, f"{crees} apprenant(s) enregistré(s) avec succès.")
        if deja_existants:
            messages.warning(
                self.request,
                "Déjà présents dans cette classe : " + ", ".join(deja_existants) + ".",
            )
        if crees == 0 and not deja_existants:
            messages.error(self.request, "Aucune ligne renseignée à enregistrer.")
        return redirect("academics:classe_detail", pk=self.classe.pk)


class ClasseMatiereCreateView(LoginRequiredMixin, CreateView):
    """Affecte une matière (avec son coefficient pour CETTE classe) à une classe."""
    model = ClasseMatiere
    form_class = ClasseMatiereForm
    template_name = "academics/classematiere_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.classe = get_object_or_404(Classe, pk=kwargs["classe_pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.classe = self.classe
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("academics:classe_detail", args=[self.classe.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["classe"] = self.classe
        return ctx