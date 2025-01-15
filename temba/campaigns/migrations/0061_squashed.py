# This is a dummy migration which will be implemented in the next release

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0060_archive_deleted_groups"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = []
