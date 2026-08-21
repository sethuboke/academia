# Academia

Application web de gestion scolaire développée avec **Django 6** : suivi des classes, des élèves, des notes (interrogations & devoirs), des absences et consultation des résultats par les élèves via un lien public sécurisé.

> Conçue pour un système éducatif francophone à deux semestres, notation sur 20, avec moyennes pondérées par coefficients.

---

## Fonctionnalités

### 🏫 Gestion académique (`academics`)
- **Années scolaires** avec notion d'année courante
- **Semestres** (S1 / S2) rattachés à une année scolaire (unicité garantie en base)
- **Classes** par année scolaire, chacune dotée d'un **lien UUID public non devinable** pour la consultation élève
- **Matières** et association classe ↔ matière (**ClasseMatiere**) avec **coefficient** (≥ 1)
- **Élèves** rattachés à une classe (unicité nom + prénom par classe)
- CRUD complet (list, detail, create, update, delete) pour chaque entité

### 📝 Notes (`grades`)
- Saisie groupée des notes : **une ligne par élève**, pour les interrogations comme pour les devoirs
- **Interrogations** : 4 maximum par matière / semestre / élève (contrainte métier)
- **Devoirs 1 et 2** : un seul de chaque par matière / semestre / élève (mise à jour si re-saisie)
- Intégrité renforcée au niveau modèle : cohérence élève ↔ classe ↔ semestre ↔ année scolaire, bornes de notes 0–20
- Workflow de validation : une note saisie reste invisible pour l'élève jusqu'à sa **validation** explicite par l'enseignant (horodatage automatique)
- **Relevé de notes** par matière/semestre avec moyenne calculée en temps réel
- Moteur de calcul **pur et testable unitairement** (`services.py`), découplé de l'ORM (`aggregations.py`) :

| Moyenne | Formule | Remarques |
|---|---|---|
| `Moy_I` | (I₁ + … + Iₙ) ÷ n | 1 ≤ n ≤ 4 interrogations |
| `Moy_M` | (Moy_I + D₁ + D₂) ÷ 3 | **moyenne partielle** si des éléments manquent |
| `Moy_Mc` | Moy_M × Coefficient | coefficient défini par classe/matière |
| `Moy_Semestre` | Σ(Moy_Mc) ÷ Σ(coefficients) | matières sans note exclues du calcul |
| `Moy_Annuelle` | (Moy_S1 + 2 × Moy_S2) ÷ 3 | None si un semestre n'est pas calculable |

> Toutes les moyennes sont **tronquées à 2 décimales** (13.336 → 13.33, jamais arrondies).

### 🗓️ Assiduité (`attendance`)
- Suivi des **absences** et **retards** par élève, avec motif et date
- Liste par classe + suppression

### 👨‍🎓 Consultation élève (`student_access`)
- Page publique accessible via le **lien UUID de la classe** : `/eleve/<uuid>/`
- L'élève s'identifie simplement par **nom + prénom**
- Seules les **notes validées** sont affichées, avec moyennes par matière, moyennes de semestre et moyenne annuelle

### 📊 Tableau de bord (`dashboard`)
- Vue d'ensemble protégée par authentification : effectifs, matières, notes, absences, dernières classes

---

## Stack technique

| Composant | Version |
|---|---|
| Python | 3.13+ |
| Django | 6.1 |
| Base de données | SQLite (développement) |

Aucune dépendance tierce lourde : interface construite en templates Django (Tailwind CSS côté front).

## Structure du projet

```
academia/
├── config/            # Configuration Django (settings, urls racine)
├── academics/         # Années scolaires, semestres, classes, matières, élèves
├── grades/
│   ├── models.py      # Interrogation, Devoir (+ contraintes métier)
│   ├── services.py    # Moteur de calcul des moyennes (fonctions pures)
│   ├── aggregations.py# Pont ORM -> moteur de calcul
│   └── views.py       # Saisie, validation, relevé
├── attendance/        # Absences et retards
├── student_access/    # Consultation publique des notes (lien UUID)
├── dashboard/         # Tableau de bord
├── audit/             # Journalisation (prévu)
└── templates/         # Templates globaux et par application
```

## Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/sethuboke/academia.git
cd academia

# 2. Créer et activer un environnement virtuel
python -m venv web
# Windows (PowerShell)
web\Scripts\activate
# Linux / macOS
source web/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Appliquer les migrations
python manage.py migrate

# 5. Créer un compte administrateur
python manage.py createsuperuser
```

## Lancement

```bash
python manage.py runserver
```

Puis ouvrir :

- **Application** : http://127.0.0.1:8000/
- **Administration Django** : http://127.0.0.1:8000/admin/

### Consultation élève

Chaque classe possède un lien public de la forme :

```
http://127.0.0.1:8000/eleve/<uuid-de-la-classe>/
```

L'UUID est visible dans la fiche de la classe (admin ou détail de classe).

## Tests

```bash
python manage.py test
```

Les tests couvrent notamment le moteur de calcul des moyennes (fonctions pures testées sans base de données) et les vues.

## ⚠️ Notes importantes avant une mise en production

- `DEBUG = True` et la `SECRET_KEY` dans `config/settings.py` sont des valeurs de développement : les externaliser (variables d'environnement / `.env`) avant tout déploiement.
- La base SQLite est adaptée au développement ; migrer vers PostgreSQL en production.
- Les apps `audit` (journalisation des modifications post-validation) sont amorcées mais pas encore implémentées.

## Feuille de route

- [ ] Journal d'audit des modifications de notes (`audit`)
- [ ] Export PDF des relevés de notes
- [ ] Gestion fine des rôles (enseignant / direction)
- [ ] Statistiques avancées dans le tableau de bord

---

## Licence

Projet à usage pédagogique — libre à vous d'ajouter une licence (MIT, GPL…) selon vos besoins.
