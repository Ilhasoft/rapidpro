# This is a dummy migration which will be implemented in the next release

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("contacts", "0197_squashed"),
        ("msgs", "0280_update_triggers"),
    ]

    operations = []
