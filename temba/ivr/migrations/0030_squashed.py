# This is a dummy migration which will be implemented in the next release

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("channels", "0187_squashed"),
        ("contacts", "0197_squashed"),
        ("ivr", "0029_squashed"),
    ]

    operations = []
