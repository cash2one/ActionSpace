# coding=utf-8
from __future__ import print_function
from __future__ import unicode_literals
from django.db import models
from django.core.validators import validate_comma_separated_integer_list, validate_ipv46_address
from om.util import *


# Create your models here.
class System(models.Model):
    name = models.CharField(max_length=100, verbose_name='系统名')
    desc = models.TextField(verbose_name='备注')

    def __str__(self):
        return get_name(self.name)

    class Meta:
        verbose_name = '系统'
        verbose_name_plural = '系统'


class Entity(models.Model):
    name = models.CharField(max_length=100, verbose_name='实体名')
    system = models.ForeignKey(System, on_delete=models.CASCADE, verbose_name='所属系统')
    desc = models.TextField(verbose_name='备注')

    def __str__(self):
        return get_name(self.name)

    class Meta:
        verbose_name = '实体'
        verbose_name_plural = '实体'


class Computer(models.Model):
    entity = models.ManyToManyField(Entity, verbose_name='所属实体')
    host = models.CharField(max_length=100, verbose_name='主机名')
    ip = models.CharField(max_length=100, verbose_name='IP地址', validators=[validate_ipv46_address])
    ENV_TYPE = (('PRD', '生产环境'), ('UAT', '测试环境'), ('FAT', '开发环境'))
    env = models.CharField(max_length=20, choices=ENV_TYPE, verbose_name='环境类型', default='FAT')
    installed_agent = models.BooleanField(default=False, verbose_name='是否已安装AGENT')
    agent_name = models.CharField(max_length=100, verbose_name='AGENT名称')
    desc = models.CharField(max_length=200, verbose_name='备注')

    def __str__(self):
        return get_name('{host}-{ip}'.format(host=self.host, ip=self.ip))

    def entity_name(self):
        return ','.join([x.name for x in self.entity.all()])
    entity_name.short_description = '实体名（列表）'

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
    desc = models.TextField(verbose_name='备注')

    def __str__(self):
        return get_name(self.name)

    def validate_job_group_list(self, save=True):
        new_job_group_id_list = str2arr(self.job_group_list)
        for group_id in new_job_group_id_list:
            if not JobGroup.objects.filter(pk=int(group_id)).exists():
                new_job_group_id_list.remove(group_id)
        if len(new_job_group_id_list) != len(str2arr(self.job_group_list)):
            self.job_group_list = ','.join(new_job_group_id_list)
            if save:
                self.save()
        return self

    class Meta:
        verbose_name = '作业流'
        verbose_name_plural = '作业流'


class JobGroup(models.Model):
    name = models.CharField(max_length=100, verbose_name='作业组名称')
    founder = models.CharField(max_length=50, verbose_name='创建人', default='NA')
    last_modified_by = models.CharField(max_length=50, verbose_name='最后修改人', default='NA')
    created_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    last_modified_time = models.DateTimeField(verbose_name="最后修改时间", auto_now=True)
    # job_group顺序内容，id用逗号分隔
    job_list = models.CharField(max_length=500, default='', blank=True, verbose_name='作业列表')
    desc = models.TextField(verbose_name='备注')

    def __str__(self):
        return get_name(self.name)

    def validate_job_list(self, save=True):
        new_job_id_list = str2arr(self.job_list)
        for job_id in new_job_id_list:
            if not Job.objects.filter(pk=int(job_id)).exists():
                new_job_id_list.remove(job_id)
        if len(new_job_id_list) != len(str2arr(self.job_list)):
            self.job_group_list = ','.join(new_job_id_list)
            if save:
                self.save()
        return self

    class Meta:
        verbose_name = '作业组'
        verbose_name_plural = '作业组'


class ExecUser(models.Model):
    name = models.CharField(max_length=100, verbose_name='执行用户')
    desc = models.TextField(verbose_name='备注')

    def __str__(self):
        return get_name(self.name)

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
    script_content = models.TextField(verbose_name='脚本内容', blank=True)
    script_param = models.CharField(max_length=100, verbose_name='脚本参数', blank=True)
    file_from_local = models.BooleanField(verbose_name='是否使用本地上传的文件', default=False)
    file_target_path = models.CharField(max_length=100, verbose_name='上传目标路径', default='NA')
    server_list = models.ManyToManyField(Computer, blank=True, verbose_name='服务器列表')
    # server_list = models.CharField(max_length=500, blank=True, default='', verbose_name="服务器列表")
    desc = models.TextField(verbose_name='备注', default='NA')

    def __str__(self):
        return get_name(self.name)

    class Meta:
        verbose_name = '作业'
        verbose_name_plural = '作业'


class Task(models.Model):
    name = models.CharField(max_length=100, default='', verbose_name='作业流名称')
    exec_user = models.CharField(max_length=100, default='NA', verbose_name='执行人')
    start_time = models.DateTimeField(verbose_name='开始时间', auto_now_add=True)  # 可以手工修改这个字段
    end_time = models.DateTimeField(verbose_name='结束时间', auto_now=True)
    STATUS = (('finish', '已执行'), ('running', '正在执行'), ('no_run', '未执行'), ('run_fail', '执行失败'))
    status = models.CharField(max_length=50, choices=STATUS, default='no_run', verbose_name='当前状态')
    async_result = models.CharField(max_length=80, default='', verbose_name='Celery的task id')
    APPROVAL_STATUS = (('Y', '通过'), ('N', '未审'), ('R', '拒绝'))
    approval_status = models.CharField(max_length=5, choices=APPROVAL_STATUS, default='N', verbose_name='审批状态')
    approval_desc = models.CharField(max_length=100, default='', verbose_name='审批描述')
    approver = models.CharField(max_length=100, default='', verbose_name='审批人')
    approval_time = models.DateTimeField(verbose_name='审批时间')

    def approval(self, approver, approval_status, approval_desc, auto_save=True):
        self.approval_status = approval_status
        self.approver = approver
        self.approval_desc = approval_desc
        self.approval_time = timezone.now()
        if auto_save:
            self.save()

    def run(self):
        self.start_time = timezone.now()
        self.status = 'running'
        self.save()

    def finish(self):
        self.end_time = timezone.now()
        self.status = 'finish'
        self.save()

    def __str__(self):
        return get_name(self.name)

    class Meta:
        verbose_name = '任务'
        verbose_name_plural = '任务'
        # app_label = '任务管理'
        permissions = (('can_approval_task', '审批任务是否可执行'),)


class TaskFlow(models.Model):
    name = models.CharField(max_length=100, verbose_name='作业流名称')
    flow_id = models.IntegerField(verbose_name='作业组ID')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, verbose_name='任务')

    class Meta:
        verbose_name = '[任务]作业流'
        verbose_name_plural = '[任务]作业流'
        # app_label = '任务管理'

    def __str__(self):
        return get_name(self.name)


class TaskJobGroup(models.Model):
    name = models.CharField(max_length=100, verbose_name='作业组名称')
    group_id = models.IntegerField(verbose_name='作业组ID')
    flow = models.ForeignKey(TaskFlow, on_delete=models.CASCADE, verbose_name='作业流')

    class Meta:
        verbose_name = '[任务]作业组'
        verbose_name_plural = '[任务]作业组'
        # app_label = '任务管理'

    def __str__(self):
        return get_name(self.name)


class TaskJob(models.Model):
    name = models.CharField(max_length=100, verbose_name='作业名称')
    job_id = models.IntegerField(verbose_name='作业ID')
    group = models.ForeignKey(TaskJobGroup, on_delete=models.CASCADE, verbose_name='作业组')
    TYPE_CHOOSE = (('SCRIPT', '脚本执行'), ('FILE', '文件传输'))
    job_type = models.CharField(max_length=50, choices=TYPE_CHOOSE, default='SCRIPT', verbose_name='作业类型')
    SCRIPT_CHOOSE = (('PY', 'python脚本'), ('SHELL', 'shell脚本'), ('BAT', '批处理脚本'))
    script_type = models.CharField(max_length=50, choices=SCRIPT_CHOOSE, default='PY', blank=True, verbose_name='脚本类型')
    script_content = models.TextField(verbose_name='脚本内容', blank=True)
    script_param = models.CharField(max_length=100, verbose_name='脚本参数', blank=True)
    begin_time = models.DateTimeField(verbose_name='开始时间')
    end_time = models.DateTimeField(verbose_name='结束时间')
    STATUS = (('finish', '已执行'), ('running', '正在执行'), ('no_run', '未执行'), ('run_fail', '执行失败'))
    status = models.CharField(max_length=50, choices=STATUS, default='no_run', verbose_name='当前状态')
    pause_need_confirm = models.BooleanField(verbose_name='暂停是否已确认', default=False)
    pause_when_finish = models.BooleanField(verbose_name='执行完成后是否暂停', default=False)
    pause_finish_tip = models.CharField(max_length=100, verbose_name='执行完成暂停提示', default='执行完成，请确认后继续。')
    exec_output = models.TextField(verbose_name='执行结果输出', blank=True)
    exec_user = models.CharField(max_length=100, default='', verbose_name='执行用户')
    server_list = models.TextField(max_length=10000, default='', verbose_name='服务器列表')

    class Meta:
        verbose_name = '[任务]作业'
        verbose_name_plural = '[任务]作业'
        # app_label = '任务管理'

    def __str__(self):
        return get_name(self.name)


class CommonScript(models.Model):
    name = models.CharField(max_length=100, verbose_name='作业名称')
    TYPES = (('py', 'python脚本'), ('shell', 'shell脚本'), ('bat', '批处理脚本'))
    script_type = models.CharField(max_length=50, choices=TYPES, default='shell', verbose_name='脚本类型')
    content = models.TextField(max_length=10000, default='', verbose_name='脚本内容')
    desc = models.CharField(max_length=400, default='', verbose_name='说明')

    class Meta:
        verbose_name = '常用脚本'
        verbose_name_plural = '常用脚本'

    def __str__(self):
        return get_name(self.name)
