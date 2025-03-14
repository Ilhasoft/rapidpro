# Generated by Django 5.1.2 on 2024-10-24 18:08

from django.db import migrations


def assign_agents_to_default_team(apps, schema_editor):  # pragma: no cover
    OrgMembership = apps.get_model("orgs", "OrgMembership")

    for membership in OrgMembership.objects.filter(role_code="T"):
        membership.team = membership.org.teams.get(is_default=True)
        membership.save(update_fields=["team"])


class Migration(migrations.Migration):

    dependencies = [
        ("orgs", "0153_invitation_role_code_invitation_team_and_more"),
        ("tickets", "0068_backfill_default_teams"),
    ]

    operations = [
        migrations.RunPython(assign_agents_to_default_team, migrations.RunPython.noop),
    ]
