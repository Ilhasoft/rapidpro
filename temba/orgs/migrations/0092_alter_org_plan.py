# Generated by Django 3.2.9 on 2023-06-01 02:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0091_alter_org_plan'),
    ]

    operations = [
        migrations.AlterField(
            model_name='org',
            name='plan',
            field=models.CharField(default='topups', help_text='What plan your organization is on', max_length=16, verbose_name='Plan'),
        ),
    ]