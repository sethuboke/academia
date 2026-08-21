import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS = ["*"]

from django.test import Client
from django.contrib.auth.models import User

with open("test_output.txt", "w", encoding="utf-8") as f:
    try:
        if not User.objects.filter(username="testuser").exists():
            User.objects.create_user("testuser", password="testpass123")

        c = Client()

        # 1. Page de login (publique)
        r = c.get("/accounts/login/")
        f.write(f"LOGIN: {r.status_code}\n")

        # 2. Accès non authentifié -> redirection vers login
        r = c.get("/")
        f.write(f"DASHBOARD (non auth): {r.status_code} (attendu 302)\n")

        # 3. Connexion
        ok = c.login(username="testuser", password="testpass123")
        f.write(f"LOGIN OK: {ok}\n")

        # 4. Dashboard (authentifié)
        r = c.get("/")
        f.write(f"DASHBOARD (auth): {r.status_code}\n")

        # 5. Liste des classes
        r = c.get("/classes/")
        f.write(f"CLASSES: {r.status_code}\n")

        # 6. Années scolaires
        r = c.get("/annees-scolaires/")
        f.write(f"ANNEES LIST: {r.status_code}\n")
        r = c.get("/annees-scolaires/ajouter/")
        f.write(f"ANNEES CREATE: {r.status_code}\n")

        # 7. Semestres
        r = c.get("/semestres/")
        f.write(f"SEMESTRES LIST: {r.status_code}\n")
        r = c.get("/semestres/ajouter/")
        f.write(f"SEMESTRES CREATE: {r.status_code}\n")

        # 8. Matières
        r = c.get("/matieres/")
        f.write(f"MATIERES LIST: {r.status_code}\n")
        r = c.get("/matieres/ajouter/")
        f.write(f"MATIERES CREATE: {r.status_code}\n")

        # 9. Page de consultation élève (UUID inexistant -> 404)
        r = c.get("/eleve/00000000-0000-0000-0000-000000000000/")
        f.write(f"STUDENT ACCESS (404 attendu): {r.status_code}\n")

        f.write("=== TESTS TERMINÉS ===\n")
    except Exception as e:
        import traceback
        f.write(f"EXCEPTION: {type(e).__name__}: {e}\n")
        f.write(traceback.format_exc())