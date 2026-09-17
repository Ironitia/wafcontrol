from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wafinstaller", "0008_allow_policy_revision_snapshot_reuse"),
    ]

    operations = [
        migrations.AddField(
            model_name="ruleexclusion",
            name="source_ip",
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
    ]
