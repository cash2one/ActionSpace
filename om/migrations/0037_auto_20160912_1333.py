# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-12 05:33
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('om', '0036_auto_20160912_1324'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='task',
            name='exec_type',
        ),
        migrations.AddField(
            model_name='flow',
            name='is_quick_flow',
            field=models.BooleanField(default=False, verbose_name='\u662f\u5426\u4e3a\u4e34\u65f6\u4f5c\u4e1a\u6d41'),
        ),
    ]