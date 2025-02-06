# Generated by Django 5.1.4 on 2024-12-10 18:06

from django.db import migrations

SQL = """
----------------------------------------------------------------------
-- Determines the item count scope for a msg record
----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION temba_msg_countscope(_msg msgs_msg) RETURNS TEXT STABLE AS $$
BEGIN
  IF _msg.direction = 'I' THEN
    -- incoming IVR messages aren't part of any system labels
    IF _msg.msg_type = 'V' THEN
      RETURN NULL;
    END IF;

    IF _msg.visibility = 'V' AND _msg.status = 'H' AND _msg.flow_id IS NULL THEN
      RETURN 'msgs:folder:I';
    ELSIF _msg.visibility = 'V' AND _msg.status = 'H' AND _msg.flow_id IS NOT NULL THEN
      RETURN 'msgs:folder:W';
    ELSIF _msg.visibility = 'A'  AND _msg.status = 'H' THEN
      RETURN 'msgs:folder:A';
    END IF;
  ELSE
    IF _msg.VISIBILITY = 'V' THEN
      IF _msg.status = 'I' OR _msg.status = 'Q' OR _msg.status = 'E' THEN
        RETURN 'msgs:folder:O';
      ELSIF _msg.status = 'W' OR _msg.status = 'S' OR _msg.status = 'D' OR _msg.status = 'R' THEN
        RETURN 'msgs:folder:S';
      ELSIF _msg.status = 'F' THEN
        RETURN 'msgs:folder:X';
      END IF;
    END IF;
  END IF;

  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

----------------------------------------------------------------------
-- Handles INSERT statements on msg table
----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION temba_msg_on_insert() RETURNS TRIGGER AS $$
BEGIN
    -- add broadcast counts for all new broadcast values
    INSERT INTO msgs_broadcastmsgcount("broadcast_id", "count", "is_squashed")
    SELECT broadcast_id, count(*), FALSE FROM newtab WHERE broadcast_id IS NOT NULL GROUP BY broadcast_id;

    -- add system label counts for all messages which belong to a system label
    INSERT INTO msgs_systemlabelcount("org_id", "label_type", "count", "is_squashed")
    SELECT org_id, temba_msg_determine_system_label(newtab), count(*), FALSE FROM newtab
    WHERE temba_msg_determine_system_label(newtab) IS NOT NULL
    GROUP BY org_id, temba_msg_determine_system_label(newtab);

    -- add positive item counts for all rows which belong to a folder
    INSERT INTO orgs_itemcount("org_id", "scope", "count", "is_squashed")
    SELECT org_id, temba_msg_countscope(newtab), count(*), FALSE FROM newtab
    WHERE temba_msg_countscope(newtab) IS NOT NULL
    GROUP BY 1, 2;

    -- add channel counts for all messages with a channel
    INSERT INTO channels_channelcount("channel_id", "count_type", "day", "count", "is_squashed")
    SELECT channel_id, temba_msg_determine_channel_count_code(newtab), created_on::date, count(*), FALSE FROM newtab
    WHERE channel_id IS NOT NULL GROUP BY channel_id, temba_msg_determine_channel_count_code(newtab), created_on::date;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

----------------------------------------------------------------------
-- Handles DELETE statements on msg table
----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION temba_msg_on_delete() RETURNS TRIGGER AS $$
BEGIN
    -- add negative system label counts for all messages that belonged to a system label
    INSERT INTO msgs_systemlabelcount("org_id", "label_type", "count", "is_squashed")
    SELECT org_id, temba_msg_determine_system_label(oldtab), -count(*), FALSE FROM oldtab
    WHERE temba_msg_determine_system_label(oldtab) IS NOT NULL
    GROUP BY org_id, temba_msg_determine_system_label(oldtab);

    -- add negative item counts for all rows that belonged to a folder
    INSERT INTO orgs_itemcount("org_id", "scope", "count", "is_squashed")
    SELECT org_id, temba_msg_countscope(oldtab), -count(*), FALSE FROM oldtab
    WHERE temba_msg_countscope(oldtab) IS NOT NULL
    GROUP BY 1, 2;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

----------------------------------------------------------------------
-- Handles UPDATE statements on msg table
----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION temba_msg_on_update() RETURNS TRIGGER AS $$
BEGIN
    -- add negative counts for all old non-null system labels that don't match the new ones
    INSERT INTO msgs_systemlabelcount("org_id", "label_type", "count", "is_squashed")
    SELECT o.org_id, temba_msg_determine_system_label(o), -count(*), FALSE FROM oldtab o
    INNER JOIN newtab n ON n.id = o.id
    WHERE temba_msg_determine_system_label(o) IS DISTINCT FROM temba_msg_determine_system_label(n) AND temba_msg_determine_system_label(o) IS NOT NULL
    GROUP BY 1, 2;

    -- add counts for all new system labels that don't match the old ones
    INSERT INTO msgs_systemlabelcount("org_id", "label_type", "count", "is_squashed")
    SELECT n.org_id, temba_msg_determine_system_label(n), count(*), FALSE FROM newtab n
    INNER JOIN oldtab o ON o.id = n.id
    WHERE temba_msg_determine_system_label(o) IS DISTINCT FROM temba_msg_determine_system_label(n) AND temba_msg_determine_system_label(n) IS NOT NULL
    GROUP BY 1, 2;

    -- add negative item counts for all rows that belonged to a folder they no longer belong to
    INSERT INTO orgs_itemcount("org_id", "scope", "count", "is_squashed")
    SELECT o.org_id, temba_msg_countscope(o), -count(*), FALSE FROM oldtab o
    INNER JOIN newtab n ON n.id = o.id
    WHERE temba_msg_countscope(o) IS DISTINCT FROM temba_msg_countscope(n) AND temba_msg_countscope(o) IS NOT NULL
    GROUP BY 1, 2;

    -- add positive item counts for all rows that now belong to a folder they didn't belong to
    INSERT INTO orgs_itemcount("org_id", "scope", "count", "is_squashed")
    SELECT n.org_id, temba_msg_countscope(n), count(*), FALSE FROM newtab n
    INNER JOIN oldtab o ON o.id = n.id
    WHERE temba_msg_countscope(o) IS DISTINCT FROM temba_msg_countscope(n) AND temba_msg_countscope(n) IS NOT NULL
    GROUP BY 1, 2;

    -- add negative old-state label counts for all messages being archived/restored
    INSERT INTO msgs_labelcount("label_id", "is_archived", "count", "is_squashed")
    SELECT ml.label_id, o.visibility != 'V', -count(*), FALSE FROM oldtab o
    INNER JOIN newtab n ON n.id = o.id
    INNER JOIN msgs_msg_labels ml ON ml.msg_id = o.id
    WHERE (o.visibility = 'V' AND n.visibility != 'V') or (o.visibility != 'V' AND n.visibility = 'V')
    GROUP BY 1, 2;

    -- add new-state label counts for all messages being archived/restored
    INSERT INTO msgs_labelcount("label_id", "is_archived", "count", "is_squashed")
    SELECT ml.label_id, n.visibility != 'V', count(*), FALSE FROM newtab n
    INNER JOIN oldtab o ON o.id = n.id
    INNER JOIN msgs_msg_labels ml ON ml.msg_id = n.id
    WHERE (o.visibility = 'V' AND n.visibility != 'V') or (o.visibility != 'V' AND n.visibility = 'V')
    GROUP BY 1, 2;

    -- add new flow activity counts for incoming messages now marked as handled by a flow
    INSERT INTO flows_flowactivitycount("flow_id", "scope", "count", "is_squashed")
    SELECT s.flow_id, unnest(ARRAY[
            format('msgsin:hour:%s', extract(hour FROM NOW())),
            format('msgsin:dow:%s', extract(isodow FROM NOW())),
            format('msgsin:date:%s', NOW()::date)
        ]), s.msgs, FALSE
    FROM (
        SELECT n.flow_id, count(*) AS msgs FROM newtab n INNER JOIN oldtab o ON o.id = n.id
        WHERE n.direction = 'I' AND o.flow_id IS NULL AND n.flow_id IS NOT NULL
        GROUP BY 1
    ) s;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

----------------------------------------------------------------------
-- Determines the item count scope for a broadcast record
----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION temba_broadcast_countscope(_broadcast msgs_broadcast) RETURNS TEXT STABLE AS $$
BEGIN
  IF _broadcast.schedule_id IS NOT NULL AND _broadcast.is_active = TRUE THEN
    RETURN 'msgs:folder:E';
  END IF;

  RETURN NULL;
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

    -- add positive item counts for all rows which belong to a folder
    INSERT INTO orgs_itemcount("org_id", "scope", "count", "is_squashed")
    SELECT org_id, temba_broadcast_countscope(newtab), count(*), FALSE FROM newtab
    WHERE temba_broadcast_countscope(newtab) IS NOT NULL
    GROUP BY 1, 2;

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

    -- add negative item counts for all rows that belonged to a folder
    INSERT INTO orgs_itemcount("org_id", "scope", "count", "is_squashed")
    SELECT org_id, temba_broadcast_countscope(oldtab), -count(*), FALSE FROM oldtab
    WHERE temba_broadcast_countscope(oldtab) IS NOT NULL
    GROUP BY 1, 2;

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

    -- add negative counts for all old non-null item count scopes that don't match the new ones
    INSERT INTO orgs_itemcount("org_id", "scope", "count", "is_squashed")
    SELECT o.org_id, temba_broadcast_countscope(o), -count(*), FALSE FROM oldtab o
    INNER JOIN newtab n ON n.id = o.id
    WHERE temba_broadcast_countscope(o) IS DISTINCT FROM temba_broadcast_countscope(n) AND temba_broadcast_countscope(o) IS NOT NULL
    GROUP BY 1, 2;

    -- add counts for all new system labels that don't match the old ones
    INSERT INTO msgs_systemlabelcount("org_id", "label_type", "count", "is_squashed")
    SELECT n.org_id, temba_broadcast_determine_system_label(n), count(*), FALSE FROM newtab n
    INNER JOIN oldtab o ON o.id = n.id
    WHERE temba_broadcast_determine_system_label(o) IS DISTINCT FROM temba_broadcast_determine_system_label(n) AND temba_broadcast_determine_system_label(n) IS NOT NULL
    GROUP BY n.org_id, temba_broadcast_determine_system_label(n);

    -- add positive counts for all new non-null item counts that don't match the old ones
    INSERT INTO orgs_itemcount("org_id", "scope", "count", "is_squashed")
    SELECT n.org_id, temba_broadcast_countscope(n), count(*), FALSE FROM newtab n
    INNER JOIN oldtab o ON o.id = n.id
    WHERE temba_broadcast_countscope(o) IS DISTINCT FROM temba_broadcast_countscope(n) AND temba_broadcast_countscope(n) IS NOT NULL
    GROUP BY 1, 2;

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

    -- add call count for all new rows
    INSERT INTO orgs_itemcount("org_id", "scope", "count", "is_squashed")
    SELECT org_id, 'msgs:folder:C', count(*), FALSE FROM newtab GROUP BY 1;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

----------------------------------------------------------------------
-- Handles DELETE statements on ivr_call table
----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION temba_ivrcall_on_delete() RETURNS TRIGGER AS $$
BEGIN
    -- add negative count for all rows being deleted manually
    INSERT INTO msgs_systemlabelcount(org_id, label_type, count, is_squashed)
    SELECT org_id, 'C', -count(*), FALSE
    FROM oldtab GROUP BY org_id;

    -- add negative count for all rows being deleted manually
    INSERT INTO orgs_itemcount("org_id", "scope", "count", "is_squashed")
    SELECT org_id, 'msgs:folder:C', -count(*), FALSE FROM oldtab GROUP BY 1;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("msgs", "0277_alter_broadcastmsgcount_count_alter_labelcount_count_and_more"),
    ]

    operations = [migrations.RunSQL(SQL)]
