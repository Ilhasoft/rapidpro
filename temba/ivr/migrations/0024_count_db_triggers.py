# Generated by Django 4.1.9 on 2023-05-29 16:26

from django.db import migrations

SQL = """
----------------------------------------------------------------------
-- Handles DELETE statements on ivr_call table
----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION temba_ivrcall_on_delete() RETURNS TRIGGER AS $$
BEGIN
    -- add negative count for all rows being deleted manually
    INSERT INTO msgs_systemlabelcount(org_id, label_type, count, is_squashed)
    SELECT org_id, 'C', -count(*), FALSE
    FROM oldtab GROUP BY org_id;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

----------------------------------------------------------------------
-- Handles INSERT statements on ivr_call table
----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION temba_ivrcall_on_insert() RETURNS TRIGGER AS $$
BEGIN
    -- add call count for all new rows
    INSERT INTO msgs_systemlabelcount(org_id, label_type, count, is_squashed)
    SELECT org_id, 'C', count(*), FALSE FROM newtab GROUP BY org_id;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER temba_ivrcall_on_delete
AFTER DELETE ON ivr_call REFERENCING OLD TABLE AS oldtab
FOR EACH STATEMENT EXECUTE PROCEDURE temba_ivrcall_on_delete();

CREATE TRIGGER temba_ivrcall_on_insert
AFTER INSERT ON ivr_call REFERENCING NEW TABLE AS newtab
FOR EACH STATEMENT EXECUTE PROCEDURE temba_ivrcall_on_insert();
"""


class Migration(migrations.Migration):
    dependencies = [("ivr", "0023_squashed")]

    operations = [migrations.RunSQL(SQL)]
