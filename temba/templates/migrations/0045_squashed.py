# This is a dummy migration which will be implemented in the next release

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("channels", "0187_squashed"),
        ("orgs", "0162_squashed"),
        ("templates", "0044_unsupported_to_pending"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = []
