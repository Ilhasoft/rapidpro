# Generated by Django 4.2.2 on 2023-07-05 18:02

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    This migration is because the state of the constraint is slightly different in Django 4.2, but the SQL it produces
    is the same, so it can be safely faked.
    """

    dependencies = [
        ("contacts", "0175_alter_contactfield_agent_access"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="contacturn", name="non_empty_scheme_and_path"),
        migrations.AddConstraint(
            model_name="contacturn",
            constraint=models.CheckConstraint(
                check=models.Q(("scheme", ""), ("path", ""), _connector="OR", _negated=True),
                name="non_empty_scheme_and_path",
            ),
        ),
    ]
