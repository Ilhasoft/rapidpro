# This is a dummy migration which will be implemented in the next release

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("airtime", "0033_squashed"),
        ("channels", "0187_squashed"),
        ("classifiers", "0014_squashed"),
        ("flows", "0352_squashed"),
        ("orgs", "0162_squashed"),
        ("request_logs", "0018_httplog_httplog_org_flows_only_error"),
    ]

    operations = []
