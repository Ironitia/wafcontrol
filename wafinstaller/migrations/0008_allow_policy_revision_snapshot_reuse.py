from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("wafinstaller", "0007_webauthncredential"),
    ]

    operations = [
        migrations.AlterField(
            model_name="policyrevision",
            name="config_revision",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="policy_revisions",
                to="wafinstaller.configrevision",
            ),
        ),
    ]
