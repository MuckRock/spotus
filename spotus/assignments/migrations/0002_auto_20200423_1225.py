# Generated by Django 3.0.5 on 2020-04-23 12:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='data',
            name='url',
            field=models.URLField(max_length=255, verbose_name='URL'),
        ),
    ]
