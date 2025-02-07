# This is a dummy migration which will be implemented in the next release

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0063_squashed"),
        ("contacts", "0198_squashed"),
        ("flows", "0352_squashed"),
        ("ivr", "0030_squashed"),
        ("orgs", "0162_squashed"),
        ("templates", "0045_squashed"),
        ("tickets", "0074_squashed"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = []
