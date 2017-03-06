# coding=utf-8
from django.contrib import admin
from rangefilter.filter import DateRangeFilter  # DateTimeRangeFilter
from om.models import *
from django.db import models
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from ckeditor.widgets import CKEditorWidget
from guardian.admin import GuardedModelAdmin
from django.conf import settings
from om.CodeEditor import CodeEditor
# from jet.admin import CompactInline


if settings.USE_DJANGO_CELERY and False:
    from kombu.transport.django import models as kombu_models

    admin.site.register(kombu_models.Message)

# Register your models here.
admin.site.unregister(FlatPage)


# noinspection PyProtectedMember
class ReadOnlyModelAdmin(GuardedModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        if obj:
            self.readonly_fields = [field.name for field in obj.__class__._meta.fields]
        return self.readonly_fields


@admin.register(FlatPage)
class FlatPageCustom(FlatPageAdmin):
    # 'widget': CKEditorWidget(config_name='awesome_ckeditor')
    formfield_overrides = {
        models.TextField: {'widget': CKEditorWidget(config_name='default')}
    }


class EntityInline(admin.StackedInline):
    model = Entity
    show_change_link = True
    extra = 0
    verbose_name = '实体'
    verbose_name_plural = '实体'


@admin.register(System)
class SystemAdmin(GuardedModelAdmin):
    list_display = ('id', 'name', 'desc')
    inlines = [EntityInline]
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name')


class ComputerInline(admin.TabularInline):
    model = Computer.entity.through
    raw_id_fields = ('entity',)
    show_change_link = True
    extra = 3
    verbose_name = '主机'
    verbose_name_plural = '主机'


class JobInline(admin.TabularInline):
    model = Job.server_list.through
    extra = 3
    show_change_link = True
    verbose_name = '作业'
    verbose_name_plural = '作业'


@admin.register(Entity)
class EntityAdmin(GuardedModelAdmin):
    list_display = ('id', 'name', 'system', 'desc')
    inlines = [ComputerInline]
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name', 'system__name')


class JobServerFileInline(admin.TabularInline):
    model = Job.file_name.through
    extra = 0
    show_change_link = True
    verbose_name = '主机'
    verbose_name_plural = '主机'


@admin.register(ServerFile)
class ServerFileAdmin(GuardedModelAdmin):
    list_display = ('id', 'name', 'founder', 'upload_time')
    list_display_links = ('id', 'name',)
    inlines = [JobServerFileInline]
    search_fields = ('id', 'name', 'founder', 'upload_time', 'desc')


class ComputerGroupInline(admin.TabularInline):
    model = ComputerGroup.computer_list.through
    extra = 0
    show_change_link = True
    verbose_name = '主机'
    verbose_name_plural = '主机'


@admin.register(Computer)
class ComputerAdmin(GuardedModelAdmin):
    list_display = ('id', 'env', 'sys', 'ip', 'installed_agent', 'agent_name', 'entity_name')
    filter_horizontal = ('entity',)
    inlines = [JobInline, ComputerGroupInline]
    list_display_links = ('id', 'agent_name')
    search_fields = ('id', 'entity__name', 'env', 'host', 'ip', 'sys', 'installed_agent')
    actions = ['mark_logstash', 'mark_flume']
    list_filter = ('env', 'sys', 'installed_agent')

    def mark_logstash(self, _, queryset):
        ent = Entity.objects.filter(name='logstash')
        if ent.exists():
            [c.entity.add(ent.first()) for c in queryset]
    mark_logstash.short_description = '添加到logstash实体'

    def mark_flume(self, _, queryset):
        ent = Entity.objects.filter(name='flume')
        if ent.exists():
            [c.entity.add(ent.first()) for c in queryset]
    mark_flume.short_description = '添加到flume实体'


@admin.register(MacAddr)
class MacAddrAdmin(GuardedModelAdmin):
    list_display = ('id', 'mac_hex', 'interface', 'minion')
    search_fields = ('id', 'mac_hex', 'interface')


@admin.register(ComputerGroup)
class ComputerGroupAdmin(GuardedModelAdmin):
    list_display = ('id', 'name', 'computer', 'founder', 'last_modified_by', 'env')
    filter_horizontal = ('computer_list',)
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name', 'computers_list', 'founder', 'last_modified_by')


@admin.register(Flow)
class FlowAdmin(GuardedModelAdmin):
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name')
    readonly_fields = ('created_time', 'last_modified_time',)
    list_display = (
        'id', 'name', 'founder', 'is_quick_flow', 'last_modified_by', 'job_group_list', 'desc'
    )


@admin.register(JobGroup)
class JobGroupAdmin(GuardedModelAdmin):
    readonly_fields = ('created_time', 'last_modified_time',)
    list_display = ('id', 'name', 'founder', 'last_modified_by', 'job_list', 'desc')


@admin.register(ExecUser)
class ExecUserAdmin(GuardedModelAdmin):
    list_display = ('name', 'desc')


@admin.register(Job)
class JobAdmin(GuardedModelAdmin):
    list_display_links = ('name',)
    readonly_fields = ('created_time', 'last_modified_time')
    filter_vertical = ('server_list',)
    list_display = (
        'id', 'name', 'founder', 'exec_user', 'pause_when_finish', 'last_modified_by'
    )
    list_filter = ('founder', 'exec_user', 'last_modified_by')

    fieldsets = (
        (None, {
            'fields': (
                'name', 'founder', 'last_modified_by', 'created_time',
                'last_modified_time', 'job_type', 'pause_when_finish',
                'pause_finish_tip', 'server_list', 'desc'
            )
        }),
        ('脚本选项', {
            'classes': ('collapse',),
            'fields': ('script_type', 'exec_user', 'script_content',
                       'script_param', 'file_name', 'target_name', 'server_list', 'desc'),
        }),
        ('文件选项', {
            'classes': ('collapse',),
            'fields': ('file_name', 'target_name'),
        })
    )

    formfield_overrides = {
        models.TextField: {
            'widget': CodeEditor(
                related_id='id_script_type', mode="shell",
                theme="ambiance", config={'fixedGutter': True, 'readOnly': False},
            )
        }
    }


class TaskFlowInline(admin.StackedInline):
    model = TaskFlow
    show_change_link = True
    extra = 0
    verbose_name = '[任务]作业流'
    verbose_name_plural = '[任务]作业流'
    readonly_fields = ['flow_id', 'name']


@admin.register(Task)
class TaskAdmin(GuardedModelAdmin):
    list_display = ('id', 'name', 'approval_status', 'status')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name', 'exec_user')
    inlines = [TaskFlowInline]
    list_filter = (
        'start_time', 'end_time', 'status', 'approval_status', 'approval_time',
        'founder', 'exec_user', 'approver'
    )


class TaskJobGroupInline(admin.StackedInline):
    model = TaskJobGroup
    show_change_link = True
    extra = 0
    verbose_name = '[任务]作业组'
    verbose_name_plural = '[任务]作业组'
    readonly_fields = ['group_id', 'name', 'step']


@admin.register(TaskFlow)
class TaskFlowAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'name', 'flow_id', 'task')
    list_display_links = ('id', 'name')
    inlines = [TaskJobGroupInline]


class TaskJobInline(admin.StackedInline):
    model = TaskJob
    show_change_link = True
    extra = 0
    verbose_name = '[任务]作业'
    verbose_name_plural = '[任务]作业'
    # readonly_fields = ['name', 'job_id', 'step']
    readonly_fields = [
        'name', 'job_id', 'group', 'job_type', 'script_type', 'file_name',
        'target_name', 'begin_time', 'end_time', 'status', 'step',
        'pause_need_confirm', 'pause_when_finish', 'pause_finish_tip'
    ]


@admin.register(TaskJobGroup)
class TaskJobGroupAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'name', 'group_id', 'flow', 'step')
    list_display_links = ('id', 'name')
    inlines = [TaskJobInline]


@admin.register(TaskJob)
class TaskJobAdmin(GuardedModelAdmin):
    list_display = ('id', 'name', 'job_id', 'step', 'group', 'status')
    list_display_links = ('id', 'name')
    readonly_fields = [
        'name', 'job_id', 'group', 'job_type', 'script_type', 'file_name',
        'target_name', 'begin_time', 'end_time', 'status', 'step',
        'pause_need_confirm', 'pause_when_finish', 'pause_finish_tip'
    ]


@admin.register(CommonScript)
class CommonScriptAdmin(GuardedModelAdmin):
    list_display = ('id', 'name', 'script_type', 'desc')
    list_display_links = ('id', 'name')

    formfield_overrides = {
        models.TextField: {
            'widget': CodeEditor(
                related_id='id_script_type', mode="shell",
                theme="ambiance", config={'fixedGutter': True, 'readOnly': False},
            )
        }
    }


class MacAddrInline(admin.StackedInline):
    model = MacAddr
    show_change_link = True
    extra = 0
    verbose_name = 'MAC地址信息'
    verbose_name_plural = 'MAC地址列表'


@admin.register(SaltMinion)
class SaltMinionAdmin(GuardedModelAdmin):
    list_display = ('name', 'status', 'env', 'os')
    search_fields = ('name', 'status', 'env', 'os')
    inlines = [MacAddrInline]
    list_filter = ('status', 'env', 'os')


@admin.register(CallLog)
class CallLogAdmin(GuardedModelAdmin):
    list_display = ('id', 'type', 'user', 'action', 'date_time')
    search_fields = ('id', 'type', 'user__username', 'action')
    list_filter = (('date_time', DateRangeFilter), 'type', 'user')


@admin.register(MailGroup)
class MailGroupAdmin(GuardedModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('id', 'name')
