# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-13 03:29
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('om', '0041_auto_20160912_1555'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='curr_step',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='om.Job', verbose_name='\u5f53\u524d\u6267\u884c\u4f5c\u4e1a'),
        ),
    ]
