# coding=utf-8
from django.db import models


# Create your models here.
class Action(models.Model):
    name = models.CharField(max_length=100, verbose_name='名称')
    founder = models.CharField(max_length=50, verbose_name='创建人', default='NA')
    last_modified_by = models.CharField(max_length=50, verbose_name='最后修改人', default='NA')
    created_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    last_modified_time = models.DateTimeField(verbose_name='最后修改时间', auto_now=True)
    STATUS = (('running', '正在执行'), ('success', '执行成功'), ('fail', '执行失败'), ('no_run', '未执行'))
    status = models.CharField(max_length=50, choices=STATUS, default='no_run', verbose_name='状态')
    async_result = models.CharField(max_length=80, blank=True, default='', verbose_name='任务标识')
    desc = models.CharField(max_length=400, verbose_name='备注', default='NA')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '操作'
        verbose_name_plural = '操作'
