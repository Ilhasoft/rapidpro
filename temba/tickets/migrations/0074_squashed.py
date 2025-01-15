# This is a dummy migration which will be implemented in the next release

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("contacts", "0197_squashed"),
        ("flows", "0352_squashed"),
        ("orgs", "0162_squashed"),
        ("tickets", "0073_delete_ticketcount"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = []
