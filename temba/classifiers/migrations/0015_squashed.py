# This is a dummy migration which will be implemented in the next release

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("classifiers", "0014_squashed"),
        ("orgs", "0162_squashed"),
    ]

    operations = []
