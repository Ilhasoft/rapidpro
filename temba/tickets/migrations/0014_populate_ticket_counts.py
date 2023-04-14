# Generated by Django 2.2.20 on 2021-07-26 18:40

from collections import defaultdict

from django.db import migrations

STATUS_OPEN = "O"
STATUS_CLOSED = "C"


def populate_ticket_counts(apps, schema_editor):  # pragma: no cover
    Org = apps.get_model("orgs", "Org")

    for org in Org.objects.exclude(tickets=None):
        org.ticket_counts.all().delete()

        open_counts = defaultdict(int)
        closed_counts = defaultdict(int)

        for ticket in org.tickets.only("assignee", "status"):
            if ticket.status == STATUS_OPEN:
                open_counts[ticket.assignee] += 1
            else:
                closed_counts[ticket.assignee] += 1

        for assignee, count in open_counts.items():
            org.ticket_counts.create(assignee=assignee, status=STATUS_OPEN, count=count, is_squashed=True)
        for assignee, count in closed_counts.items():
            org.ticket_counts.create(assignee=assignee, status=STATUS_CLOSED, count=count, is_squashed=True)

        total_open = sum(open_counts.values())
        total_closed = sum(closed_counts.values())
        print(f"Updated ticket counts for org '{org.name}' (open={total_open}, closed={total_closed})")


def reverse(apps, schema_editor):  # pragma: no cover
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("tickets", "0013_ticket_counts"),
    ]

    operations = [migrations.RunPython(populate_ticket_counts, reverse)]
