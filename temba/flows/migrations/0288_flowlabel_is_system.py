# Generated by Django 4.0.4 on 2022-05-10 14:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("flows", "0287_alter_flowlabel_unique_together_flowlabel_created_by_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="flowlabel",
            name="is_system",
            field=models.BooleanField(default=False),
        ),
    ]