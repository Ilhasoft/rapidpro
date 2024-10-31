# Generated by Django 4.0.7 on 2022-11-03 21:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("orgs", "0104_alter_org_brand"), ("sql", "0004_squashed")]

    operations = [
        migrations.RemoveField(
            model_name="topupcredits",
            name="topup",
        ),
        migrations.AlterField(
            model_name="org",
            name="uses_topups",
            field=models.BooleanField(null=True),
        ),
        migrations.DeleteModel(
            name="CreditAlert",
        ),
        migrations.DeleteModel(
            name="TopUpCredits",
        ),
    ]
