# Generated by Django 3.2.22 on 2024-03-06 01:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wpp_products", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="availability",
            field=models.CharField(
                choices=[("in stock", "in stock"), ("out of stock", "out of stock")], default="in stock", max_length=12
            ),
            preserve_default=False,
        ),
    ]
