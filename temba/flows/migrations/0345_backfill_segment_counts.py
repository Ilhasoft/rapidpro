# Generated by Django 5.1.2 on 2024-11-28 14:01

import itertools

from django.db import migrations, transaction
from django.db.models import Sum


def backfill_segment_counts(apps, schema_editor):  # pragma: no cover
    Flow = apps.get_model("flows", "Flow")

    flow_ids = list(Flow.objects.filter(is_active=True).order_by("id").values_list("id", flat=True))

    print(f"Backfilling segment counts for {len(flow_ids)} flows...")

    num_backfilled = 0

    for id_batch in itertools.batched(flow_ids, 500):
        flows = Flow.objects.filter(id__in=id_batch).only("id", "metadata").order_by("id")
        for flow in flows:
            backfill_for_flow(apps, flow)

        num_backfilled += len(flows)
        print(f"> updated counts for {num_backfilled} of {len(flow_ids)} flows")


def backfill_for_flow(apps, flow) -> int:  # pragma: no cover
    FlowActivityCount = apps.get_model("flows", "FlowActivityCount")

    # no waits then no engagement counts
    exit_uuids = flow.metadata.get("waiting_exit_uuids", [])
    if not exit_uuids:
        return

    exit_counts = flow.path_counts.filter(from_uuid__in=exit_uuids)

    with transaction.atomic():
        to_create = []

        def add_count(scope: str, count: int):
            if count > 0:
                to_create.append(FlowActivityCount(flow=flow, scope=scope, count=count, is_squashed=True))

        by_segment = exit_counts.values("from_uuid", "to_uuid").annotate(total=Sum("count"))
        for count in by_segment:
            add_count(f"segment:{count['from_uuid']}:{count['to_uuid']}", count["total"])

        flow.counts.filter(scope__startswith="segment:").delete()
        FlowActivityCount.objects.bulk_create(to_create)
        return len(to_create)


def apply_manual():  # pragma: no cover
    from django.apps import apps

    backfill_segment_counts(apps, None)


class Migration(migrations.Migration):

    dependencies = [("flows", "0344_update_triggers")]

    operations = [migrations.RunPython(backfill_segment_counts, migrations.RunPython.noop)]
