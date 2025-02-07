# This is a dummy migration which will be implemented in the next release

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0062_squashed"),
        ("contacts", "0197_squashed"),
        ("flows", "0352_squashed"),
        ("orgs", "0162_squashed"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = []
