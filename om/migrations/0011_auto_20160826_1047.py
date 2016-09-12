# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-08-26 02:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('om', '0010_auto_20160826_1027'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='job',
            name='job_group',
        ),
        migrations.RemoveField(
            model_name='jobgroup',
            name='flow',
        ),
        migrations.AddField(
            model_name='jobgroup',
            name='job_list',
            field=models.CharField(default='', max_length=500, verbose_name='\u4f5c\u4e1a\u7ec4\u5e8f\u5217'),
        ),
        migrations.AlterField(
            model_name='flow',
            name='job_group_list',
            field=models.CharField(default='', max_length=500, verbose_name='\u4efb\u52a1\u7ec4\u5e8f\u5217'),
        ),
    ]