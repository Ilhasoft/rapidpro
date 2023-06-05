# Generated by Django 4.1.9 on 2023-06-05 19:03

import django.db.models.deletion
from django.db import migrations, models

SQL = """
----------------------------------------------------------------------
-- Determines the (mutually exclusive) system label for a broadcast record
----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION temba_broadcast_determine_system_label(_broadcast msgs_broadcast) RETURNS CHAR(1) STABLE AS $$
BEGIN
  IF _broadcast.schedule_id IS NOT NULL AND _broadcast.is_active = TRUE THEN
    RETURN 'E';
  END IF;

  RETURN NULL; -- does not match any label
END;
$$ LANGUAGE plpgsql;

----------------------------------------------------------------------
-- Handles INSERT statements on broadcast table
----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION temba_broadcast_on_insert() RETURNS TRIGGER AS $$
BEGIN
    -- add system label counts for all rows which belong to a system label
    INSERT INTO msgs_systemlabelcount("org_id", "label_type", "count", "is_squashed")
    SELECT org_id, temba_broadcast_determine_system_label(newtab), count(*), FALSE FROM newtab
    WHERE temba_broadcast_determine_system_label(newtab) IS NOT NULL
    GROUP BY org_id, temba_broadcast_determine_system_label(newtab);

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

----------------------------------------------------------------------
-- Handles UPDATE statements on broadcast table
----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION temba_broadcast_on_update() RETURNS TRIGGER AS $$
BEGIN
    -- add negative counts for all old non-null system labels that don't match the new ones
    INSERT INTO msgs_systemlabelcount("org_id", "label_type", "count", "is_squashed")
    SELECT o.org_id, temba_broadcast_determine_system_label(o), -count(*), FALSE FROM oldtab o
    INNER JOIN newtab n ON n.id = o.id
    WHERE temba_broadcast_determine_system_label(o) IS DISTINCT FROM temba_broadcast_determine_system_label(n) AND temba_broadcast_determine_system_label(o) IS NOT NULL
    GROUP BY o.org_id, temba_broadcast_determine_system_label(o);

    -- add counts for all new system labels that don't match the old ones
    INSERT INTO msgs_systemlabelcount("org_id", "label_type", "count", "is_squashed")
    SELECT n.org_id, temba_broadcast_determine_system_label(n), count(*), FALSE FROM newtab n
    INNER JOIN oldtab o ON o.id = n.id
    WHERE temba_broadcast_determine_system_label(o) IS DISTINCT FROM temba_broadcast_determine_system_label(n) AND temba_broadcast_determine_system_label(n) IS NOT NULL
    GROUP BY n.org_id, temba_broadcast_determine_system_label(n);

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

----------------------------------------------------------------------
-- Handles DELETE statements on broadcast table
----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION temba_broadcast_on_delete() RETURNS TRIGGER AS $$
BEGIN
    -- add negative system label counts for all rows that belonged to a system label
    INSERT INTO msgs_systemlabelcount("org_id", "label_type", "count", "is_squashed")
    SELECT org_id, temba_broadcast_determine_system_label(oldtab), -count(*), FALSE FROM oldtab
    WHERE temba_broadcast_determine_system_label(oldtab) IS NOT NULL
    GROUP BY org_id, temba_broadcast_determine_system_label(oldtab);

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER temba_broadcast_on_insert
AFTER INSERT ON msgs_broadcast REFERENCING NEW TABLE AS newtab
FOR EACH STATEMENT EXECUTE PROCEDURE temba_broadcast_on_insert();

CREATE TRIGGER temba_broadcast_on_update
AFTER UPDATE ON msgs_broadcast REFERENCING OLD TABLE AS oldtab NEW TABLE AS newtab
FOR EACH STATEMENT EXECUTE PROCEDURE temba_broadcast_on_update();

CREATE TRIGGER temba_broadcast_on_delete
AFTER DELETE ON msgs_broadcast REFERENCING OLD TABLE AS oldtab
FOR EACH STATEMENT EXECUTE PROCEDURE temba_broadcast_on_delete();

DROP TRIGGER temba_broadcast_on_change_trg ON msgs_broadcast;
DROP FUNCTION temba_insert_system_label(INT, CHAR(1), INT);
DROP FUNCTION temba_broadcast_on_change();
"""


class Migration(migrations.Migration):
    dependencies = [("msgs", "0240_update_db_triggers")]

    operations = [
        migrations.AlterField(
            model_name="broadcast",
            name="org",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name="broadcasts", to="orgs.org"
            ),
        ),
        migrations.RunSQL(SQL),
    ]
