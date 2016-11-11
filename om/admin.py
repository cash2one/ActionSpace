# coding=utf-8
from django.contrib import admin
from om.models import *
from django.db import models
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from ckeditor.widgets import CKEditorWidget
from guardian.admin import GuardedModelAdmin
from django.conf import settings
from codemirror import CodeMirrorTextarea
from django.utils.safestring import mark_safe

if settings.USE_DJANGO_CELERY:
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
    list_display = ('name', 'desc')
    inlines = [EntityInline]
    search_fields = ('name',)


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
    list_display = ('name', 'system', 'desc')
    inlines = [ComputerInline]
    search_fields = ('name', 'system__name')


@admin.register(Computer)
class ComputerAdmin(GuardedModelAdmin):
    list_display = ('entity_name', 'env', 'host', 'ip', 'desc', 'installed_agent', 'agent_name')
    filter_horizontal = ('entity',)
    inlines = [JobInline]
    search_fields = ('entity__name', 'env', 'host', 'ip', 'installed_agent')


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
    filter_vertical = ('server_list',)
    list_display = (
        'id', 'name', 'founder', 'exec_user', 'pause_when_finish',
        'pause_finish_tip', 'file_from_local', 'file_target_path', 'desc'
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


@admin.register(Task)
class TaskAdmin(ReadOnlyModelAdmin):
    exclude = ('detail',)
    list_display = ('id', 'exec_user', 'start_time', 'end_time', 'status')
    list_display_links = ('id', 'exec_user')


@admin.register(TaskFlow)
class TaskFlowAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'name', 'flow_id', 'task')
    list_display_links = ('id', 'name')


@admin.register(TaskJobGroup)
class TaskJobGroupAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'name', 'group_id', 'flow')
    list_display_links = ('id', 'name')


@admin.register(TaskJob)
class TaskJobAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'name', 'job_id', 'group', 'status')
    list_display_links = ('id', 'name')


class ContentEditor(CodeMirrorTextarea):
    def render(self, name, value, attrs=None):
        if self.js_var_format is not None:
            js_var_bit = 'var %s = ' % (self.js_var_format % name)
        else:
            js_var_bit = ''
        jquery = '<script src = "//cdn.bootcss.com/jquery/3.1.0/jquery.min.js" ></script>'
        after = '''
    function set_code(val) {
        switch (val) {
        case 'py':
            content_editor.setOption("mode", "python");
            break;
        case 'shell':
            content_editor.setOption("mode", "shell");
            break;
        case 'bat':
            content_editor.setOption("mode", "perl");
            break;
        };
    }
    set_code($('#id_script_type').val())
    $('#id_script_type').change(function(){
        var script_type = $(this).children('option:selected').val();
        set_code(script_type);
    });
        '''
        output = [super(CodeMirrorTextarea, self).render(name, value, attrs),
                  '%s\n<script type="text/javascript">\n    %sCodeMirror.fromTextArea(document.getElementById(%s), %s);\n%s</script>' %
                  (jquery, js_var_bit, '"id_%s"' % name, self.option_json, after)]
        return mark_safe('\n'.join(output))


@admin.register(CommonScript)
class CommonScriptAdmin(GuardedModelAdmin):
    list_display = ('id', 'name', 'script_type', 'desc')
    list_display_links = ('id', 'name')

    formfield_overrides = {
        models.TextField: {'widget': ContentEditor(
            mode="shell",
            theme="ambiance",
            config={
                'fixedGutter': True
            },
        )}
    }
