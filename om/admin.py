# coding=utf-8
from django.contrib import admin
from om.models import System, Entity, Computer, Flow, JobGroup, ExecUser, Job, LogType, Log, Task
from django.db import models
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from ckeditor.widgets import CKEditorWidget
from guardian.admin import GuardedModelAdmin


# Register your models here.
admin.site.unregister(FlatPage)


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


@admin.register(System)
class SystemAdmin(GuardedModelAdmin):
    list_display = ('name', 'desc')
    inlines = [EntityInline]


class ComputerInline(admin.TabularInline):
    model = Computer.entity.through
    raw_id_fields = ('entity',)
    extra = 0


@admin.register(Entity)
class EntityAdmin(GuardedModelAdmin):
    list_display = ('name', 'system', 'desc')
    inlines = [ComputerInline]


@admin.register(Computer)
class ComputerAdmin(GuardedModelAdmin):
    list_display = ('host', 'ip', 'desc', 'installed_agent', 'agent_name')
    # filter_vertical = ('entity',)
    filter_horizontal = ('entity',)


@admin.register(Flow)
class FlowAdmin(GuardedModelAdmin):
    list_display_links = ('id', 'name')
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
    list_display = (
        'id', 'name', 'founder', # , 'job_type', 'script_type',
        'exec_user', 'pause_when_finish', 'pause_finish_tip',
        'file_from_local', 'file_target_path', 'server_list', 'desc'
    )

    # fieldsets = (
    #     (None, {
    #         'fields': ('name', 'job_type', 'exec_user', 'script_type')
    #     }),
    #     ('高级选项', {
    #         'classes': ('collapse',),
    #         'fields': ('pause_when_finish', 'pause_finish_tip', 'script_content',
    #                    'script_param', 'file_from_local', 'file_target_path', 'server_list', 'desc'),
    #     }),
    # )


@admin.register(LogType)
class LogTypeAdmin(GuardedModelAdmin):
    list_display = ('name', 'desc')


@admin.register(Log)
class LogAdmin(GuardedModelAdmin):
    list_display = ('id', 'log_type', 'topic', 'log_time', 'content')
    date_hierarchy = 'log_time'
    actions_on_top = False
    actions_on_bottom = True


@admin.register(Task)
class TaskAdmin(GuardedModelAdmin):
    exclude = ('detail',)
    readonly_fields = ('id', 'exec_user', 'exec_flow', 'start_time', 'end_time', 'status')
    list_display = ('id', 'exec_user', 'exec_flow', 'start_time', 'end_time', 'status')
    list_display_links = ('id', 'exec_user')
