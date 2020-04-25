# Generated by Django 3.0.5 on 2020-04-23 12:25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, help_text="Unique ID to link organizations across MuckRock's sites", unique=True, verbose_name='UUID')),
                ('name', models.CharField(help_text='Name of the organization', max_length=255, verbose_name='name')),
                ('slug', models.SlugField(help_text='Unique slug for the organization which may be used in a URL', max_length=255, unique=True, verbose_name='slug')),
                ('private', models.BooleanField(default=False, help_text='Whether or not to keep this organization and its membership list private', verbose_name='private')),
                ('individual', models.BooleanField(default=True, help_text='Is this an organization for an individual user?', verbose_name='individual')),
                ('card', models.CharField(blank=True, help_text='The brand and last 4 digits of the default credit card on file for this organization, for display purposes', max_length=255, verbose_name='card')),
                ('avatar_url', models.URLField(blank=True, help_text='A URL which points to an avatar for the organization', max_length=255, verbose_name='avatar url')),
                ('date_update', models.DateField(help_text='The date when this organizations monthly resources will be refreshed', null=True, verbose_name='date update')),
                ('payment_failed', models.BooleanField(default=False, help_text='This organizations payment method has failed and should be updated', verbose_name='payment failed')),
                ('verified_journalist', models.BooleanField(default=False, help_text='This organization is a verified jorunalistic organization', verbose_name='verified journalist')),
            ],
            options={
                'ordering': ('slug',),
                'abstract': False,
            },
        ),
    ]