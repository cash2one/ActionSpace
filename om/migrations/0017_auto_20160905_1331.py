# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-05 05:31
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('om', '0016_job_script_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='created_time',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='\u521b\u5efa\u65f6\u95f4'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='job',
            name='founder',
            field=models.CharField(default='NA', max_length=50, verbose_name='\u521b\u5efa\u4eba'),
        ),
        migrations.AddField(
            model_name='job',
            name='last_modified_by',
            field=models.CharField(default='NA', max_length=50, verbose_name='\u6700\u540e\u4fee\u6539\u4eba'),
        ),
        migrations.AddField(
            model_name='job',
            name='last_modified_time',
            field=models.DateTimeField(auto_now=True, verbose_name='\u6700\u540e\u4fee\u6539\u65f6\u95f4'),
        ),
        migrations.AddField(
            model_name='jobgroup',
            name='created_time',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='\u521b\u5efa\u65f6\u95f4'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='jobgroup',
            name='founder',
            field=models.CharField(default='NA', max_length=50, verbose_name='\u521b\u5efa\u4eba'),
        ),
        migrations.AddField(
            model_name='jobgroup',
            name='last_modified_by',
            field=models.CharField(default='NA', max_length=50, verbose_name='\u6700\u540e\u4fee\u6539\u4eba'),
        ),
        migrations.AddField(
            model_name='jobgroup',
            name='last_modified_time',
            field=models.DateTimeField(auto_now=True, verbose_name='\u6700\u540e\u4fee\u6539\u65f6\u95f4'),
        ),
        migrations.AlterField(
            model_name='flow',
            name='created_time',
            field=models.DateTimeField(auto_now_add=True, verbose_name='\u521b\u5efa\u65f6\u95f4'),
        ),
        migrations.AlterField(
            model_name='flow',
            name='founder',
            field=models.CharField(default='NA', max_length=50, verbose_name='\u521b\u5efa\u4eba'),
        ),
        migrations.AlterField(
            model_name='flow',
            name='last_modified_by',
            field=models.CharField(default='NA', max_length=50, verbose_name='\u6700\u540e\u4fee\u6539\u4eba'),
        ),
        migrations.AlterField(
            model_name='flow',
            name='last_modified_time',
            field=models.DateTimeField(auto_now=True, verbose_name='\u6700\u540e\u4fee\u6539\u65f6\u95f4'),
        ),
        migrations.AlterField(
            model_name='job',
            name='script_type',
            field=models.CharField(blank=True, choices=[('PY', 'python\u811a\u672c'), ('SHELL', 'shell\u811a\u672c'), ('BAT', '\u6279\u5904\u7406\u811a\u672c')], default='PY', max_length=50, verbose_name='\u811a\u672c\u7c7b\u578b'),
        ),
    ]
