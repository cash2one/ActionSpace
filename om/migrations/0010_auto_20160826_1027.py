# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-08-26 02:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('om', '0009_auto_20160826_1023'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flow',
            name='job_group_list',
            field=models.CharField(max_length=500, verbose_name='\u4f5c\u4e1a\u7ec4\u987a\u5e8f'),
        ),
    ]