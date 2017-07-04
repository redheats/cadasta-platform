# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-07-04 06:39
from __future__ import unicode_literals

import accounts.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_otp.util


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_add_change_pw'),
    ]

    operations = [
        migrations.CreateModel(
            name='VerificationDevice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='The human-readable name of this device.', max_length=64)),
                ('confirmed', models.BooleanField(default=True, help_text='Is this device ready for use?')),
                ('unverified_phone', models.CharField(max_length=16)),
                ('secret_key', models.CharField(default=accounts.models.default_key, help_text='Hex-encoded secret key to generate totp tokens.', max_length=40, unique=True, validators=[django_otp.util.hex_validator])),
                ('last_verified_counter', models.BigIntegerField(default=-1, help_text='The counter value of the latest verified token.The next token must be at a higher counter value.It makes sure a token is used only once.')),
            ],
            options={
                'verbose_name': 'Verification Device',
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='historicaluser',
            name='verify_email_by',
        ),
        migrations.RemoveField(
            model_name='user',
            name='verify_email_by',
        ),
        migrations.AddField(
            model_name='historicaluser',
            name='phone',
            field=models.CharField(blank=True, db_index=True, default=None, max_length=16, null=True, verbose_name='phone number'),
        ),
        migrations.AddField(
            model_name='historicaluser',
            name='phone_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='phone',
            field=models.CharField(blank=True, default=None, max_length=16, null=True, unique=True, verbose_name='phone number'),
        ),
        migrations.AddField(
            model_name='user',
            name='phone_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='historicaluser',
            name='email',
            field=models.EmailField(blank=True, db_index=True, default=None, max_length=254, null=True, verbose_name='email address'),
        ),
        migrations.AlterField(
            model_name='historicaluser',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(blank=True, default=None, max_length=254, null=True, unique=True, verbose_name='email address'),
        ),
        migrations.AlterField(
            model_name='user',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='verificationdevice',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
