# coding=utf-8
from __future__ import unicode_literals
from django.db import models
from django.core.validators import validate_comma_separated_integer_list, validate_ipv46_address


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
    ip = models.CharField(max_length=100, verbose_name='IP地址', validators=[validate_ipv46_address])
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
    founder = models.CharField(max_length=50, verbose_name='创建人', default='NA')
    last_modified_by = models.CharField(max_length=50, verbose_name='最后修改人', default='NA')
    created_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    last_modified_time = models.DateTimeField(verbose_name='最后修改时间', auto_now=True)
    is_quick_flow = models.BooleanField(default=False, verbose_name='是否为快速执行作业流')
    # job_group顺序内容，id用逗号分隔
    job_group_list = models.CharField(max_length=500, default='', validators=[validate_comma_separated_integer_list], verbose_name='作业组列表')
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
    founder = models.CharField(max_length=50, verbose_name='创建人', default='NA')
    last_modified_by = models.CharField(max_length=50, verbose_name='最后修改人', default='NA')
    created_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    last_modified_time = models.DateTimeField(verbose_name="最后修改时间", auto_now=True)
    pause_when_finish = models.BooleanField(default=False, verbose_name='执行完成后是否暂停')
    pause_when_error = models.BooleanField(default=True, verbose_name='执行失败后是否暂停')
    # job_group顺序内容，id用逗号分隔
    job_list = models.CharField(max_length=500, default='', verbose_name='作业列表')
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
    founder = models.CharField(max_length=50, verbose_name='创建人', default='NA')
    last_modified_by = models.CharField(max_length=50, verbose_name='最后修改人', default='NA')
    created_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    last_modified_time = models.DateTimeField(verbose_name="最后修改时间", auto_now=True)
    TYPE_CHOOSE = (('SCRIPT', '脚本执行'), ('FILE', '文件传输'))
    job_type = models.CharField(max_length=50, choices=TYPE_CHOOSE, default='SCRIPT', verbose_name='作业类型')
    SCRIPT_CHOOSE = (('PY', 'python脚本'), ('SHELL', 'shell脚本'), ('BAT', '批处理脚本'))
    script_type = models.CharField(max_length=50, choices=SCRIPT_CHOOSE, default='PY', blank=True, verbose_name='脚本类型')
    exec_user = models.ForeignKey(ExecUser, verbose_name='执行用户', blank=False)
    pause_when_finish = models.BooleanField(verbose_name='执行完成后是否暂停', default=False)
    pause_finish_tip = models.CharField(max_length=100, verbose_name='执行完成暂停提示', default='执行完成，请确认后继续。')
    pause_when_error = models.BooleanField(verbose_name='执行失败后是否暂停', default=True)
    pause_error_tip = models.CharField(max_length=100, verbose_name='执行错误暂停提示', default='执行出错，请确认。')
    script_content = models.TextField(verbose_name='脚本内容', blank=True)
    script_param = models.CharField(max_length=100, verbose_name='脚本参数', blank=True)
    file_from_local = models.BooleanField(verbose_name='是否使用本地上传的文件', default=False)
    file_target_path = models.CharField(max_length=100, verbose_name='上传目标路径', default='NA')
    server_list = models.CharField(max_length=500, blank=True, default='', verbose_name="服务器列表")
    desc = models.TextField(verbose_name='备注', default='NA')

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


class Task(models.Model):
    exec_user = models.CharField(max_length=100, default='NA', verbose_name='执行人')
    exec_flow = models.ForeignKey(Flow, verbose_name='执行内容')
    start_time = models.DateTimeField(verbose_name='开始时间', auto_now_add=True)  # 可以手工修改这个字段
    end_time = models.DateTimeField(verbose_name='结束时间', auto_now=True)
    TASK_STATUS = (
        ('success', '执行成功'),
        ('error', '执行报错'),
        ('running', '正在执行'),
        ('no_run', '未执行')
    )
    task_status = models.CharField(max_length=50, choices=TASK_STATUS, default='no_run', verbose_name='当前状态')

    class Meta:
        verbose_name = '任务'
        verbose_name_plural = '任务'

