# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-07 06:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('om', '0022_auto_20160907_1343'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='server_list',
            field=models.CharField(default='', max_length=500, verbose_name='\u670d\u52a1\u5668\u5217\u8868'),
        ),
    ]