# Generated by Django 3.0.5 on 2020-04-16 14:43

from django.conf import settings
import django.contrib.postgres.fields.jsonb
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import taggit.managers


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('taggit', '0003_taggeditem_add_unique_index'),
    ]

    operations = [
        migrations.CreateModel(
            name='Assignment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='title')),
                ('slug', models.SlugField(max_length=255, verbose_name='slug')),
                ('datetime_created', models.DateTimeField(default=django.utils.timezone.now, verbose_name='datetime created')),
                ('datetime_opened', models.DateTimeField(blank=True, null=True, verbose_name='datetime opened')),
                ('datetime_closed', models.DateTimeField(blank=True, null=True, verbose_name='datetime closed')),
                ('status', models.IntegerField(choices=[(0, 'Draft'), (1, 'Open'), (2, 'Closed')], default=0, verbose_name='status')),
                ('description', models.TextField(help_text='May use markdown', verbose_name='description')),
                ('data_limit', models.PositiveSmallIntegerField(default=3, help_text='Number of times each data assignment will be completed (by different users) - only used if using data for this assignment', validators=[django.core.validators.MinValueValidator(1)], verbose_name='data limit')),
                ('multiple_per_page', models.BooleanField(default=False, help_text='This is useful for cases when there may be multiple records of interest per data source', verbose_name='allow multiple submissions per data item')),
                ('user_limit', models.BooleanField(default=True, help_text='Is the user limited to completing this form only once? (else, it is unlimited) - only used if not using data for this assignment', verbose_name='user limit')),
                ('registration', models.IntegerField(choices=[(0, 'Required'), (1, 'Off'), (2, 'Optional')], default=0, help_text='Is registration required to complete this assignment?', verbose_name='registration')),
                ('submission_emails', models.TextField(verbose_name='submission emails')),
                ('featured', models.BooleanField(default=False, help_text='Featured assignments will appear on the homepage.', verbose_name='featured')),
                ('ask_public', models.BooleanField(default=True, help_text='Add a field asking users if we can publically credit them for their response', verbose_name='ask public')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='assignments', to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
            options={
                'verbose_name': 'assignment',
                'permissions': (('form_assignment', 'Can view and fill out the assignments for this assignment'),),
            },
        ),
        migrations.CreateModel(
            name='Data',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(max_length=255, verbose_name='url')),
                ('metadata', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, verbose_name='metadata')),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='data', to='assignments.Assignment', verbose_name='assignment')),
            ],
            options={
                'verbose_name': 'assignment data',
            },
        ),
        migrations.CreateModel(
            name='Field',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=255, verbose_name='label')),
                ('type', models.CharField(choices=[('text', 'text'), ('select', 'select'), ('checkbox2', 'checkbox2'), ('checkbox-group', 'checkbox-group'), ('date', 'date'), ('number', 'number'), ('textarea', 'textarea'), ('header', 'header'), ('paragraph', 'paragraph')], max_length=15, verbose_name='type')),
                ('help_text', models.CharField(blank=True, max_length=255, verbose_name='help text')),
                ('min', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='minimum')),
                ('max', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='maximum')),
                ('required', models.BooleanField(default=True, verbose_name='required')),
                ('gallery', models.BooleanField(default=False, verbose_name='gallery')),
                ('order', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='order')),
                ('deleted', models.BooleanField(default=False, verbose_name='deleted')),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fields', to='assignments.Assignment', verbose_name='assignment')),
            ],
            options={
                'verbose_name': 'assignment field',
                'ordering': ('order',),
                'unique_together': {('assignment', 'label'), ('assignment', 'order')},
            },
        ),
        migrations.CreateModel(
            name='Response',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public', models.BooleanField(default=False, help_text='Publically credit the user who submitted this response in the gallery', verbose_name='public')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='ip address')),
                ('datetime', models.DateTimeField(default=django.utils.timezone.now, verbose_name='datetime')),
                ('skip', models.BooleanField(default=False, verbose_name='skip')),
                ('number', models.PositiveSmallIntegerField(default=1, verbose_name='number')),
                ('flag', models.BooleanField(default=False, verbose_name='flag')),
                ('gallery', models.BooleanField(default=False, verbose_name='gallery')),
                ('edit_datetime', models.DateTimeField(blank=True, null=True, verbose_name='edit datetime')),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='responses', to='assignments.Assignment', verbose_name='response')),
                ('data', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='responses', to='assignments.Data', verbose_name='data')),
                ('edit_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='edited_assignment_responses', to=settings.AUTH_USER_MODEL, verbose_name='edit user')),
                ('tags', taggit.managers.TaggableManager(help_text='A comma-separated list of tags.', through='taggit.TaggedItem', to='taggit.Tag', verbose_name='Tags')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='assignment_responses', to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
            options={
                'verbose_name': 'assignment response',
            },
        ),
        migrations.CreateModel(
            name='Value',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(blank=True, max_length=2000, verbose_name='value')),
                ('original_value', models.CharField(blank=True, max_length=2000, verbose_name='original_value')),
                ('field', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='values', to='assignments.Field', verbose_name='field')),
                ('response', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='values', to='assignments.Response', verbose_name='response')),
            ],
            options={
                'verbose_name': 'assignment value',
            },
        ),
        migrations.CreateModel(
            name='Choice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('choice', models.CharField(max_length=255, verbose_name='choice')),
                ('value', models.CharField(max_length=255, verbose_name='value')),
                ('order', models.PositiveSmallIntegerField(verbose_name='order')),
                ('field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='choices', to='assignments.Field', verbose_name='field')),
            ],
            options={
                'verbose_name': 'assignment choice',
                'ordering': ('order',),
                'unique_together': {('field', 'order'), ('field', 'choice')},
            },
        ),
    ]
