from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0001_initial"),
    ]

    operations = [
        # Champs obligatoires ajoutés à Eleve : les élèves déjà enregistrés
        # reçoivent un défaut ponctuel ("N" / "M") lors du backfill, puis la
        # contrainte NOT NULL sans défaut s'applique (preserve_default=False) :
        # toute nouvelle saisie doit fournir explicitement statut et genre.
        migrations.AddField(
            model_name="eleve",
            name="statut",
            field=models.CharField(
                choices=[("N", "Nouveau"), ("R", "Redoublant")],
                default="N",
                max_length=1,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="eleve",
            name="genre",
            field=models.CharField(
                choices=[("M", "Masculin"), ("F", "Féminin")],
                default="M",
                max_length=1,
            ),
            preserve_default=False,
        ),
    ]
