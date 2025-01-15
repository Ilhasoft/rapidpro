# This is a dummy migration which will be implemented in the next release

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("contacts", "0198_squashed"),
        ("notifications", "0030_squashed"),
        ("orgs", "0162_squashed"),
    ]

    operations = []
