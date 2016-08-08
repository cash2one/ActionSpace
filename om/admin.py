# coding=utf-8
from django.contrib import admin
from om.models import System, Entity, Computer, Flow, JobGroup, JobType, ExecUser, Job, LogType, Log
from django.db import models
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from ckeditor.widgets import CKEditorWidget


# Register your models here.
admin.site.unregister(FlatPage)


@admin.register(FlatPage)
class FlatPageCustom(FlatPageAdmin):
    # 'widget': CKEditorWidget(config_name='awesome_ckeditor')
    formfield_overrides = {
        models.TextField: {
            'widget': CKEditorWidget(config_name='default')
            }
    }


class EntityInline(admin.StackedInline):
    model = Entity
    show_change_link = True
    extra = 0


@admin.register(System)
class SystemAdmin(admin.ModelAdmin):
    list_display = ('name', 'desc')
    inlines = [EntityInline]


class ComputerInline(admin.TabularInline):
    model = Computer.entity.through
    raw_id_fields = ('entity',)
    extra = 0


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ('name', 'system', 'desc')
    inlines = [ComputerInline]


@admin.register(Computer)
class ComputerAdmin(admin.ModelAdmin):
    list_display = ('host', 'ip', 'desc', 'installed_agent', 'agent_name')
    # filter_vertical = ('entity',)
    filter_horizontal = ('entity',)


class JobGroupInline(admin.StackedInline):
    model = JobGroup
    extra = 0


@admin.register(Flow)
class FlowAdmin(admin.ModelAdmin):
    list_display = ('name', 'desc')
    inlines = [JobGroupInline]


class JobInline(admin.StackedInline):
    model = Job
    extra = 0


@admin.register(JobGroup)
class JobGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'flow', 'desc')
    inlines = [JobInline]


@admin.register(JobType)
class JobTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'desc')


@admin.register(ExecUser)
class ExecUserAdmin(admin.ModelAdmin):
    list_display = ('name', 'desc')


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'job_group', 'job_type', 'exec_user', 'pause_when_finish',
        'pause_when_error', 'script_content', 'file_from_local', 'file_target_path',
        'desc'
    )

    fieldsets = (
        (None, {
            'fields': ('name', 'job_group', 'job_type', 'exec_user')
        }),
        ('高级选项', {
            'classes': ('collapse',),
            'fields': ('pause_when_finish', 'pause_when_error',
                       'script_content', 'file_from_local', 'file_target_path', 'desc'),
        }),
    )


@admin.register(LogType)
class LogTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'desc')


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ('id', 'log_type', 'topic', 'log_time', 'content')
    date_hierarchy = 'log_time'
    actions_on_top = False
    actions_on_bottom = True
