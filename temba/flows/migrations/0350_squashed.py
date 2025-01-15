# This is a dummy migration which will be implemented in the next release

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("channels", "0187_squashed"),
        ("classifiers", "0014_squashed"),
        ("contacts", "0196_squashed"),
        ("flows", "0349_alter_flowactivitycount_count_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = []
