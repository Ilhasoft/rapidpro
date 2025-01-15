# This is a dummy migration which will be implemented in the next release

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("channels", "0188_squashed"),
        ("contacts", "0198_squashed"),
        ("flows", "0353_squashed"),
        ("msgs", "0281_squashed"),
        ("orgs", "0162_squashed"),
        ("schedules", "0028_squashed"),
        ("templates", "0045_squashed"),
        ("tickets", "0074_squashed"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = []
