# This is a dummy migration which will be implemented in the next release

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("channels", "0186_alter_channelcount_count"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = []
