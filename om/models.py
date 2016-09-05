# coding=utf-8
from __future__ import unicode_literals
from django.db import models


# Create your models here.
class System(models.Model):
    name = models.CharField(max_length=100, verbose_name='系统名')
    desc = models.TextField(verbose_name='备注')

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = '系统'
        verbose_name_plural = '系统'


class Entity(models.Model):
    name = models.CharField(max_length=100, verbose_name='实体名')
    system = models.ForeignKey(System, on_delete=models.CASCADE, verbose_name='所属系统')
    desc = models.TextField(verbose_name='备注')

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = '实体'
        verbose_name_plural = '实体'


class Computer(models.Model):
    entity = models.ManyToManyField(Entity, verbose_name='所属实体')
    host = models.CharField(max_length=100, verbose_name='主机名')
    ip = models.CharField(max_length=100, verbose_name='IP地址')
    installed_agent = models.BooleanField(default=False, verbose_name='是否已安装AGENT')
    agent_name = models.CharField(max_length=100, verbose_name='AGENT名称')
    desc = models.TextField(verbose_name='备注')

    def __unicode__(self):
        return self.ip

    class Meta:
        verbose_name = '主机'
        verbose_name_plural = '主机'


class Flow(models.Model):
    name = models.CharField(max_length=100, verbose_name='作业流名称')
    founder = models.CharField(max_length=50, verbose_name='创建人')
    last_modified_by = models.CharField(max_length=50, verbose_name='最后修改人')
    created_time = models.DateTimeField(verbose_name="创建时间")
    last_modified_time = models.DateTimeField(verbose_name="最后修改时间")
    # job_group顺序内容，id用逗号分隔
    job_group_list = models.CharField(max_length=500, default='', verbose_name="作业组序列")
    pause_when_finish = models.BooleanField(default=False, verbose_name='执行完成后是否暂停')
    pause_when_error = models.BooleanField(default=True, verbose_name='执行失败后是否暂停')
    desc = models.TextField(verbose_name='备注')

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = '作业流'
        verbose_name_plural = '作业流'


class JobGroup(models.Model):
    name = models.CharField(max_length=100, verbose_name='作业组名称')
    pause_when_finish = models.BooleanField(default=False, verbose_name='执行完成后是否暂停')
    pause_when_error = models.BooleanField(default=True, verbose_name='执行失败后是否暂停')
    # job_group顺序内容，id用逗号分隔
    job_list = models.CharField(max_length=500, default='', verbose_name="作业组序列")
    desc = models.TextField(verbose_name='备注')

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = '作业组'
        verbose_name_plural = '作业组'


class ExecUser(models.Model):
    name = models.CharField(max_length=100, verbose_name='执行用户')
    desc = models.TextField(verbose_name='备注')

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = '执行用户'
        verbose_name_plural = '执行用户'


class Job(models.Model):
    name = models.CharField(max_length=100, verbose_name='作业名称')
    TYPE_CHOOSE = (('SCRIPT', '脚本执行'), ('FILE', '文件传输'))
    job_type = models.CharField(max_length=50, choices=TYPE_CHOOSE, default='SCRIPT', verbose_name='作业类型')
    SCRIPT_CHOOSE = (('PY', 'python脚本'), ('SHELL', 'shell脚本'), ('BAT', '批处理脚本'))
    script_type = models.CharField(max_length=50, choices=SCRIPT_CHOOSE, default='PY', blank=True, verbose_name='脚本类型')
    exec_user = models.ForeignKey(ExecUser, verbose_name='执行用户')
    pause_when_finish = models.BooleanField(default=False, verbose_name='执行完成后是否暂停')
    pause_finish_tip = models.CharField(max_length=100, verbose_name='执行完成暂停提示', default='执行完成，请确认后继续。')
    pause_when_error = models.BooleanField(default=True, verbose_name='执行失败后是否暂停')
    pause_error_tip = models.CharField(max_length=100, verbose_name='执行错误暂停提示', default='执行出错，请确认。')
    script_content = models.TextField(verbose_name='脚本内容')
    file_from_local = models.BooleanField(default=True, verbose_name='是否使用本地上传的文件')
    file_target_path = models.CharField(max_length=100, verbose_name='上传目标路径')
    desc = models.TextField(verbose_name='备注')

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = '作业'
        verbose_name_plural = '作业'


class LogType(models.Model):
    name = models.CharField(max_length=100, verbose_name='日志类型')
    desc = models.TextField(verbose_name='备注')

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = '日志类型'
        verbose_name_plural = '日志类型'


class Log(models.Model):
    log_type = models.ForeignKey(LogType, verbose_name='类型')
    topic = models.CharField(max_length=100, verbose_name='主题')
    log_time = models.DateTimeField(verbose_name='时间')
    content = models.TextField(verbose_name='内容')

    def __unicode__(self):
        return self.topic

    class Meta:
        verbose_name = '日志'
        verbose_name_plural = '日志'
