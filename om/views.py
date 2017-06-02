# coding=utf-8
from django.contrib import auth
from django.http import HttpResponseRedirect, HttpResponse
# from guardian.shortcuts import get_perms
# noinspection PyUnresolvedReferences
from django.views.decorators.cache import cache_page
# noinspection PyUnresolvedReferences
from om.util import *
from django.contrib.auth.decorators import login_required
# from guardian.decorators import permission_required
from django.http import JsonResponse
# noinspection PyUnresolvedReferences
from django.shortcuts import get_object_or_404, render
# noinspection PyUnresolvedReferences
from django.utils import timezone
from om.form import JobForm, JobGroupForm, FlowForm, TaskItemForm, ChgPwdForm, MailGroupForm
from om.models import *
from djcelery.models import PeriodicTask, IntervalSchedule, CrontabSchedule
from datetime import datetime as dt
from ActionSpace import settings
# from django.db import connection
from om.ftputil import Ftp
import json
import time
from django_select2.views import AutoResponseView
from utils.util import join_activity


# @login_required
def index(request):
    settings.logger.info(request.user.username)
    host_nginx = {
        'UAT': {
            'notebook': 'notebook_uat_url',
            'flower': 'flower_uat_url',
            'redis': 'redis_uat_url'
        },
        'PRD': {
            'notebook': 'notebook_prd_url',
            'flower': 'flower_prd_url',
            'redis': 'redis_prd_url'
        }
    }
    # noinspection PyShadowingNames
    return render(request, 'om/index.html', {
        'user': request.user, 'host': host_nginx[settings.OM_ENV],
        'join_activity': join_activity(request.user.username) or request.user.is_superuser
    })


# @login_required
def default_content(request):
    settings.logger.info(request.user.username)
    utc_date = timezone.datetime.utcnow().replace(tzinfo=timezone.utc)
    this_month_task_list = Task.objects.filter(
        start_time__year=utc_date.year,
        start_time__month=utc_date.month
    )
    context = {
        'today_task_count': Task.objects.filter(start_time__gte=utc_date.date()).count(),
        'month_task_running': this_month_task_list.filter(status='running').count(),
        'month_task_finish': this_month_task_list.filter(status='finish').count(),
        'month_task_run_fail': this_month_task_list.filter(status='run_fail').count(),
        'month_task_no_run': this_month_task_list.filter(status='no_run').count(),
        'server_count': Computer.objects.count(),
        'flow_count': Flow.objects.filter(is_quick_flow=False).count(),
        'auto_task_count': PeriodicTask.objects.filter(task='om.util.celery_auto_task').count(),
        'config_file_count': ServerFile.objects.count()
    }
    return render(request, 'om/home.html', context)


@login_required
def quick_exec_script(request):
    context = {
        'saved': False,
        'result': True,
        'error_msg': 'NA',
        'users': None,
        'scripts': None
    }
    if not request.user.has_perm('om.can_do_quick_script'):
        return no_permission(request)
    if request.method == 'POST':
        context['saved'] = True
        try:
            code_type = {'python': 'PY', 'shell': 'SHELL', 'bat': 'BAT'}
            code_mode = request.POST['code_mode']
            exec_user = request.POST['exec_user']
            script_content = request.POST['script_content']
            name = request.POST['name']
            server_list = [x['ip'] for x in json.loads(request.POST['server_list'])]
            job = Job.objects.create(
                name=name, job_type='SCRIPT', script_type=code_type[code_mode],
                script_content=script_content, script_param='',
                exec_user=ExecUser.objects.get(name=exec_user)
            )
            job.server_list.add(*[Computer.objects.get(ip=x) for x in server_list])
            job.save()
            quick_script_exec(job, request.user.username)
        except Exception as e:
            context['result'] = False
            context['error_msg'] = str(e)
        return render(request, 'om/quick_exec_script.html', context)
    else:
        context['users'] = ExecUser.objects.all().values(
            'name') if request.user.is_superuser else ExecUser.objects.exclude(name='root').values('name')
        context['scripts'] = CommonScript.objects.all()
    settings.logger.info(request.user.username)
    return render(request, 'om/quick_exec_script.html', context)


@login_required
def quick_upload_file(request):
    settings.logger.info(request.user.username)
    if not request.user.has_perm('om.can_do_quick_file'):
        return no_permission(request)
    if request.method == 'POST':
        name = request.POST['name']
        server_list = [x['ip'] for x in json.loads(request.POST['server_list'])]
        file_select = request.POST.getlist('file_select')
        exec_user = request.POST['exec_user']
        server_path = request.POST['server_path']
        job = Job.objects.create(
            name=name, job_type='FILE',
            exec_user=ExecUser.objects.get(name=exec_user),
            target_name=server_path
        )
        job.file_name.add(*[ServerFile.objects.get(pk=x) for x in file_select])
        job.server_list.add(*[Computer.objects.get(ip=x) for x in server_list])
        job.save()
        quick_script_exec(job, request.user.username)
        return render(request, 'om/close_this_layer.html', {'msg': '任务创建成功！'})
    return render(request, 'om/quick_upload_file.html', {
        'files': ServerFile.objects.all(),
        'users': ExecUser.objects.all().values(
            'name') if request.user.is_superuser else ExecUser.objects.exclude(name='root').values('name')
    })


@login_required
def job_quick_task(request, task_id):
    settings.logger.info('%s %s' % (request.user.username, task_id))
    try:
        job = Job.objects.get(pk=task_id)
        no_permission_json = JsonResponse({'result': 'N', 'msg': '没有权限执行该操作，请联系管理员！'})
        if job.job_type == 'SCRIPT' and not request.user.has_perm('om.can_do_quick_script'):
            return no_permission_json
        elif not request.user.has_perm('om.can_do_quick_file'):
            return no_permission_json
        task = quick_script_exec(job, request.user.username)
        return JsonResponse({'result': 'Y', 'msg': '创建成功，TASK ID为{id}！'.format(id=task.id)})
    except Job.DoesNotExist as _:
        return JsonResponse({'result': 'N', 'msg': 'JOB已不存在！'})


@login_required
def exec_flow(request):
    settings.logger.info(request.user.username)
    context = {
        'fields': [x for x in Flow._meta.fields if x.name not in ['job_group_list', 'is_quick_flow']]
    }
    return render(request, 'om/exec_flow.html', context)


@login_required
def create_task(request, flow_id, job_id):
    settings.logger.info('%s %s %s ' % (request.user.username, flow_id, job_id))
    if not request.user.has_perm('om.add_task'):
        return JsonResponse({'result': 'N', 'desc': '没有权限，请联系管理员！'})
    try:
        flow = Flow.objects.get(pk=flow_id)
        if flow.locked:
            return JsonResponse({'result': 'N', 'desc': '请先解锁！'})
        task = make_task(request.user.username, flow_id, job_id)
        return JsonResponse({'result': 'Y', 'desc': '任务已创建,ID={id}！'.format(id=task.id)})
    except Flow.DoesNotExist as e:
        settings.logger.error(repr(e))
        return JsonResponse({'result': 'N', 'desc': f'作业流[{flow_id}]不存在！'})


@login_required
def exec_task(request, task_id):
    settings.logger.info('%s %s' % (request.user.username, task_id))

    try:
        task = Task.objects.get(pk=task_id)
        if not any([request.user.has_perm('om.can_exec_approved_task'),
                    request.user.has_perm('om.can_exec_approved_task', task)]):
            return JsonResponse({'result': 'N', 'desc': '没权限执行，请联系管理员！'})
        if task.status == 'running':
            return JsonResponse({'result': 'N', 'desc': '任务[{tid}]正在执行中，请刷新页面查看状态。'.format(tid=task.id)})
        if task.async_result != '':
            return JsonResponse({'result': 'N', 'desc': '任务[{tid}]已发起过，请刷新页面查看状态。'.format(tid=task.id)})
        if task.approval_status == 'N':
            return JsonResponse({'result': 'N', 'desc': '任务[{tid}]尚未审批，请联系管理员审批。'.format(tid=task.id)})
        elif task.approval_status == 'R':
            return JsonResponse({'result': 'N', 'desc': '任务[{tid}]审批不通过，不能执行。'.format(tid=task.id)})
        if task.taskflow_set.count() > 0:
            res = celery_exec_task.delay(task.id, request.user.username)
            task.async_result = res.id
            task.save()
            return JsonResponse({'result': 'Y', 'desc': '任务[{tid}]已发送到后台执行。'.format(tid=task.id)})
        else:
            return JsonResponse({'result': 'N', 'desc': '任务[{tid}]不包含任何作业流。'.format(tid=task.id)})
    except Task.DoesNotExist as e:
        print(e)
        return JsonResponse({'result': 'N', 'desc': '任务[{tid}]不存在！'.format(tid=task_id)})


@login_required
def confirm_exec_task(request, task_id):
    settings.logger.info('%s %s' % (request.user.username, task_id))
    return JsonResponse({'result': 'Y' if task_in_prd(task_id) else 'N'})


@login_required
def redo_create_task(request, task_id):
    settings.logger.info('%s %s' % (request.user.username, task_id))
    for task in Task.objects.filter(pk=task_id):
        if not any([
            request.user.has_perm('om.add_task'),
            request.user.has_perm('om.add_task', task)
        ]):
            return JsonResponse({'result': 'N', 'desc': '没权限执行，请联系管理员！'})
        new_task = clone_task(task, request.user.username)
        if request.user.is_superuser:
            new_task.approval(request.user.username, 'Y', '审批通过', False)
        new_task.save()
        return JsonResponse({'result': 'Y', 'desc': 'ID为[{tid}]的任务已创建。'.format(tid=new_task.id)})
    return JsonResponse({'result': 'N', 'desc': 'ID为[{tid}]任务不存在！'.format(tid=task_id)})


@login_required
def task_status(request, task_id):
    settings.logger.info('%s %s' % (request.user.username, task_id))
    task = get_object_or_404(Task, pk=task_id)
    context = {
        'can_get_result': False,
        'result': ''
    }
    if task.async_result != '':
        context['can_get_result'] = True
        if task.async_result == 'auto':
            context['result'] = '自动任务不能显示'
        else:
            context['result'] = get_task_result(task.async_result)
    return render(request, 'om/task_status.html', context)


@login_required
def get_flow_list(request):
    settings.logger.info(request.user.username)
    fmt = '%Y-%m-%d %H:%M:%S'
    search_fields = [
        'pk__icontains', 'name__icontains', 'founder__icontains',
        'last_modified_by__icontains', 'desc__icontains'
    ]
    flows, flow_count = get_paged_query(
        Flow.objects.filter(is_quick_flow=False), search_fields, request, '-last_modified_time'
    )
    result = {'total': flow_count, 'rows': []}

    [result['rows'].append({
        'id': x.id, 'name': x.name, 'founder': x.founder, 'last_modified_by': x.last_modified_by,
        'created_time': dt.strftime(timezone.localtime(x.created_time), fmt), 'locked': x.locked,
        'last_modified_time': dt.strftime(timezone.localtime(x.last_modified_time), fmt),
        'recipient': x.recipient.name if x.recipient is not None else '启动人',
        'desc': x.desc
    }) for x in flows]
    return JsonResponse(result, safe=False)


@login_required
def flow_clone(request, flow_id):
    settings.logger.info('%s %s' % (request.user.username, flow_id))
    flow = Flow.objects.get(pk=flow_id)
    if not any([request.user.has_perm('om.add_flow'), request.user.has_perm('om.add_flow', flow)]):
        return JsonResponse({'result': 'N', 'desc': '没有权限，请联系管理员！'})

    if flow.locked:
        return JsonResponse({'result': 'N', 'desc': '请先解锁！'})
    now_time = timezone.now()
    timestamp = int(time.mktime(now_time.timetuple()))
    cloned_flow = Flow.objects.create()
    cloned_flow.name = '{ts}_{name}'.format(ts=timestamp, name=flow.name)
    cloned_flow.founder = request.user.username
    cloned_flow.last_modified_by = request.user.username
    cloned_flow.created_time = now_time
    cloned_flow.last_modified_time = now_time
    cloned_flow.is_quick_flow = False
    cloned_flow.recipient = flow.recipient
    cloned_flow.desc = flow.desc
    cloned_flow.job_group_list = ''
    new_group_id_list = []
    for group_id in str2arr(flow.job_group_list):
        for job_group in JobGroup.objects.filter(pk=group_id):
            job_id_list = []
            for job_id in str2arr(job_group.job_list):
                for job in Job.objects.filter(pk=job_id):
                    ora_file_name_list = job.file_name.all()
                    job.pk = None
                    job.save()
                    job.name = '{ts}_{name}'.format(ts=timestamp, name=job.name)
                    job.founder = request.user.username
                    job.last_modified_by = request.user.username
                    job.created_time = now_time
                    job.last_modified_time = now_time
                    job.file_name.add(*[x for x in ora_file_name_list])
                    job.save()
                    job_id_list.append(str(job.id))
            job_group.pk = None
            job_group.save()
            job_group.name = '{ts}_{name}'.format(ts=timestamp, name=job_group.name)
            job_group.founder = request.user.username
            job_group.last_modified_by = request.user.username
            job_group.created_time = now_time
            job_group.last_modified_time = now_time
            job_group.job_list = ','.join(job_id_list)
            job_group.save()
            new_group_id_list.append(str(job_group.id))
    cloned_flow.job_group_list = ','.join(new_group_id_list)
    cloned_flow.save()
    return JsonResponse({'result': 'Y', 'id': cloned_flow.pk})


@login_required
def flow_delete(request, flow_id, username):
    settings.logger.info('%s %s' % (request.user.username, flow_id))

    flow = Flow.objects.get(pk=flow_id)
    if not any([request.user.has_perm('om.delete_flow'), request.user.has_perm('om.delete_flow', flow)]):
        return JsonResponse({'result': 'N', 'desc': '没有权限，请联系管理员！'})

    if not any([request.user.username == username, request.user.is_superuser]):
        return JsonResponse({'result': 'N', 'desc': '不能删除别人创建的作业流！'})

    if flow.locked:
        return JsonResponse({'result': 'N', 'desc': '请先解锁！'})

    flow.delete()
    return JsonResponse({'result': 'Y'})


@login_required
def new_flow(request):
    settings.logger.info(request.user.username)
    save = {
        'saved': False,
        'result': False,
        'error_msg': 'NA'
    }

    if not request.user.has_perm('om.add_flow'):
        return no_permission(request)

    if request.method == 'POST':
        save['saved'] = True
        flow_form = FlowForm(data=request.POST)
        flow_form.save()
        flow_form.instance.founder = request.user.username
        flow_form.instance.last_modified_by = request.user.username
        flow_form.save()
        save['result'] = True
    else:
        flow_form = FlowForm()
    context = {
        'form': flow_form,
        'check_field_list': ['pause_when_finish', 'pause_when_error'],
        'disable_field_list': ['job_list_comma_sep'],
        'save': save,
    }
    return render(request, 'om/new_flow.html', context)


@login_required
def new_group(request, flow_id):
    settings.logger.info('%s %s' % (request.user.username, flow_id))
    save = {
        'saved': False,
        'result': False,
        'error_msg': 'NA'
    }

    if not request.user.has_perm('om.add_jobgroup'):
        return no_permission(request)

    if request.method == 'POST':
        save['saved'] = True
        group_form = JobGroupForm(data=request.POST)
        try:
            if group_form.is_valid():
                group = group_form.save_form(request, create=True)
                flow = get_object_or_404(Flow, pk=flow_id)
                flow.last_modified_by = request.user.username
                job_group_list = str2arr(flow.job_group_list)
                job_group_list.append(str(group.id))
                flow.job_group_list = ','.join(job_group_list)
                flow.save()
                save['result'] = True
        except Exception as e:
            save['result'] = False
            save['error_msg'] = e
    else:
        group_form = JobGroupForm()

    context = {
        'form': group_form,
        'multiselect_list': ['job_list'],
        'save': save,
    }
    return render(request, 'om/edit_group.html', context)


@login_required
def edit_group(request, group_id):
    settings.logger.info('%s %s' % (request.user.username, group_id))
    group = get_object_or_404(JobGroup, pk=group_id)
    save = {
        'saved': False,
        'result': False,
        'error_msg': 'NA'
    }

    if not any([request.user.has_perm('om.change_jobgroup'), request.user.has_perm('om.change_jobgroup', group)]):
        return no_permission(request)

    if request.method == 'POST':
        save['saved'] = True
        group_form = JobGroupForm(data=request.POST, instance=group)
        try:
            if group_form.is_valid():
                group_form.save_form(request)
                save['result'] = True
        except Exception as e:
            save['result'] = False
            save['error_msg'] = e
    else:
        group_form = JobGroupForm(instance=group)

    context = {
        'form': group_form,
        'multiselect_list': ['job_list'],
        'save': save,
    }
    return render(request, 'om/edit_group.html', context)


@login_required
def new_job(request, job_group_id):
    settings.logger.info('%s %s' % (request.user.username, job_group_id))
    save = {
        'saved': False,
        'result': False,
        'error_msg': 'NA'
    }

    if not request.user.has_perm('om.add_job'):
        return no_permission(request)

    if request.method == 'POST':
        save['saved'] = True
        job_form = JobForm(data=expand_server_list(request.POST))
        try:
            job = job_form.save_form(request, commit=False, create=True)
            job_group = get_object_or_404(JobGroup, pk=job_group_id)
            job_group.last_modified_by = request.user.username
            job_list = str2arr(job_group.job_list)
            job_list.append(str(job.id))
            job_group.job_list = ','.join(job_list)
            job_group.save()
            save['result'] = True
        except Exception as e:
            save['result'] = False
            save['error_msg'] = e
    else:
        job_form = JobForm()
        job_form.last_modified_by = request.user

    context = {
        'form': job_form,
        'check_field_list': ['pause_when_finish', 'pause_when_error', 'file_from_local'],
        'normal_check_list': ['file_name', 'server_group_list'],
        'heavy_check_list': ['server_list'],
        'security_field_list': ['exec_user'],
        'job_id': -1, 'save': save
    }
    return render(request, 'om/edit_job.html', context)


# @cache_page(3600)
@login_required
def edit_job(request, job_id):
    settings.logger.info('%s %s' % (request.user.username, job_id))
    save = {
        'saved': False,
        'result': False,
        'error_msg': 'NA'
    }
    job = get_object_or_404(Job, pk=job_id)

    if not any([request.user.has_perm('om.add_job'), request.user.has_perm('om.add_job', job)]):
        return no_permission(request)

    job.last_modified_by = request.user
    if request.method == 'POST':
        save['saved'] = True
        job_form = JobForm(data=expand_server_list(request.POST), instance=job)
        # noinspection PyBroadException
        try:
            if job_form.is_valid():
                job_form.save_form(request)
                save['result'] = True
        except Exception as e:
            save['result'] = False
            save['error_msg'] = e
    else:
        job_form = JobForm(instance=job)
    context = {
        'form': job_form,
        'check_field_list': ['pause_when_finish', 'pause_when_error', 'file_from_local'],
        'disable_field_list': ['last_modified_by', 'founder'],
        'security_field_list': ['exec_user'],
        'normal_check_list': ['file_name', 'server_group_list'],
        'heavy_check_list': ['server_list'],
        'job_id': job.id, 'save': save,
    }
    return render(request, 'om/edit_job.html', context)


@login_required
def del_job_in_group(request, group_id, job_id):
    settings.logger.info('%s %s %s' % (request.user.username, group_id, job_id))
    context = {'result': 'OK'}
    try:
        group = JobGroup.objects.get(pk=group_id)
        if not any([request.user.has_perm('om.change_jobgroup'), request.user.has_perm('om.change_jobgroup', group)]):
            return JsonResponse({'result': '没有权限执行该操作，请重新打开本页面并联系管理员授权！'})

        job_list = str2arr(group.job_list)
        if job_id in job_list:
            job_list.remove(job_id)
            group.job_list = ','.join(job_list)
            group.save()
    except JobGroup.DoesNotExist as _:
        context['result'] = '作业组不存在'
    return JsonResponse(context)


@login_required
def del_group_in_flow(request, flow_id, group_id):
    settings.logger.info('%s %s %s' % (request.user.username, flow_id, group_id))
    context = {'result': 'OK'}
    try:
        flow = Flow.objects.get(pk=flow_id)

        if not any([request.user.has_perm('om.change_flow'), request.user.has_perm('om.change_flow', flow)]):
            return JsonResponse({'result': '没有权限执行该操作，请重新打开本页面并联系管理员授权！'})

        group_list = str2arr(flow.job_group_list)
        if group_id in group_list:
            group_list.remove(group_id)
            flow.job_group_list = ','.join(group_list)
            flow.save()
    except Flow.DoesNotExist as _:
        context['result'] = '作业流不存在'
    return JsonResponse(context)


@login_required
def edit_flow(request, flow_id):
    settings.logger.info('%s %s' % (request.user.username, flow_id))
    flow = get_object_or_404(Flow, pk=flow_id)

    if not any([request.user.has_perm('om.change_flow'), request.user.has_perm('om.change_flow', flow)]):
        return no_permission(request)

    if not flow.locked or (flow.locked and flow.last_modified_by != request.user.username):
        return no_permission(request)

    flow.validate_job_group_list()
    context = {'mail_group_list': MailGroup.objects.all(), 'flow': flow, 'groups': []}
    group_list = str2arr(flow.job_group_list)
    if group_list:
        groups = [get_object_or_404(JobGroup, pk=x) for x in group_list]
        [x.validate_job_list() for x in groups]
        [context['groups'].append(
            {'group': g, 'job_list': [get_object_or_404(Job, pk=x) for x in str2arr(g.job_list)]}
        ) for g in groups]
        # Job.objects.filter(id__in=str2arr(g.job_list))
    return render(request, 'om/edit_flow.html', context)


@login_required
def save_edit_flow(request):
    settings.logger.info(request.user.username)
    result = {'result': 'Y', 'flow': 'init', 'group': 'init', 'desc': '无变化，不需要保存！'}
    if request.method == 'POST' and request.POST.keys():
        info = json.loads(list(request.POST.keys())[0])
        flow_sort = info['flow']
        if flow_sort:
            flow = Flow.objects.get(pk=int(info['id']))
            if not any([request.user.has_perm('om.change_flow'), request.user.has_perm('om.change_flow', flow)]):
                return JsonResponse({'result': 'N', 'desc': '没有权限执行该操作，请重新打开本页面并联系管理员！'})

            new_job_group_list = ','.join([x.replace('group_', '') for x in flow_sort])
            # update flow job_group_list
            if flow and flow.job_group_list != new_job_group_list:
                flow.job_group_list = new_job_group_list
                flow.save()
                result['flow'] = 'save'
                result['desc'] = '修改已保存！'
            # update jobgroup task_list
            task_change = False
            for k in flow_sort:
                group_task_list = ','.join([str2arr(x, '_', False)[-1] for x in info[k]])
                group = JobGroup.objects.get(pk=int(k.replace('group_', '')))
                if group and group.job_list != group_task_list:
                    group.job_list = group_task_list
                    group.save()
                    task_change = True
                if task_change:
                    result['group'] = 'save'
                    result['desc'] = '修改已保存！'
    return JsonResponse(result)


@login_required
def action_history(request):
    settings.logger.info(request.user.username)
    return render(request, 'om/action_history.html')


@login_required
def action_detail(request, task_id):
    settings.logger.info('%s %s' % (request.user.username, task_id))
    task = get_object_or_404(Task, pk=task_id)
    return render(request, 'om/action_detail.html', {'task': task.id})


@login_required
def detail_content(request, task_id):
    settings.logger.info('%s %s ' % (request.user.username, task_id))
    task = get_object_or_404(Task, pk=task_id)
    cost_time = 0
    if task.status == 'finish':
        cost_time = (task.end_time - task.start_time).total_seconds()
    context = {
        'task': task,
        'cost_time': cost_time
    }
    return render(request, 'om/detail_content.html', context)


@login_required
def confirm_task(request, task_id, flow_id, group_id, job_id):
    settings.logger.info('%s %s %s %s %s' % (request.user.username, task_id, flow_id, group_id, job_id))
    TaskConfirm('%s-%s-%s-%s' % (task_id, flow_id, group_id, job_id)).send_confirm()
    return JsonResponse({'result': 'OK'})


@login_required
def update_flow_name(request, username, flow_id, new_name):
    settings.logger.info('%s %s %s' % (request.user.username, str(flow_id), new_name))
    if not any([request.user.username == username, request.user.is_superuser]):
        return JsonResponse({'result': '不能修改别人创建的作业流！'})
    if len(new_name) < 5:
        return JsonResponse({'result': '作业流名称长度不能小于5！'})
    try:
        flow = Flow.objects.get(pk=flow_id)
        if not any([request.user.has_perm('om.change_flow'), request.user.has_perm('om.change_flow', flow)]):
            return JsonResponse({'result': '没有权限修改，请联系管理员！'})
        flow.name = new_name
        flow.save()
    except Flow.DoesNotExist as e:
        settings.logger.error(repr(e))
        settings.logger.error(traceback.format_exc())
        return JsonResponse({'result': '找不到id为[%s]的作业流（可能已被删除）！' % str(flow_id)})
    return JsonResponse({'result': 'Y'})


@login_required
def get_task_status(request, task_id):
    settings.logger.info('%s %s' % (request.user.username, task_id))
    t = get_object_or_404(Task, pk=task_id)
    return JsonResponse({'status': t.status})


@login_required
def choose_server(request):
    settings.logger.info(request.user.username)
    return render(request, 'om/choose_server.html')


@login_required
def choose_server_result(request):
    settings.logger.info(request.user.username)
    server_list = []
    for computer in Computer.objects.all():
        server_list.append({
            'server_ip': computer.ip,
            'server_hostname': computer.host,
            'server_status': computer.installed_agent,
        })
    return JsonResponse(server_list, safe=False)


@login_required
def get_ip_host_list(request):
    settings.logger.info(request.user.username)
    server_list = []
    for s in SaltMinion.objects.filter(os='Windows', status='up'):
        server_list.append({
            'name': s.name,
            'env': s.env
        })
    return JsonResponse(server_list, safe=False)


@login_required
def get_server_list(request):
    settings.logger.info(request.user.username)
    return JsonResponse(api_server_list(request), safe=False)


@login_required
def get_task_server_list(request):
    settings.logger.info(request.user.username)
    only_task_allow = False
    # 当启用任务权限控制，开启only_task_allow即可
    return JsonResponse(api_server_list(request, only_task_allow), safe=False)


# @login_required
def get_action_history_list(request):
    settings.logger.info(request.user.username)
    search_fields = [
        'pk__icontains', 'name__icontains', 'founder__icontains', 'exec_user__icontains',
        'status__icontains', 'status__icontains', 'async_result__icontains',
        'approval_status__icontains', 'approval_desc__icontains', 'approver__icontains'
    ]
    tasks, task_count = get_paged_query(Task.objects.all(), search_fields, request, '-start_time')
    result = {'total': task_count, 'rows': []}

    fmt = '%Y-%m-%d %H:%M:%S'
    [result['rows'].append({
        'id': t.id, 'name': t.name, 'approval_status': t.get_approval_status_display(),
        'approver': t.approver, 'approval_desc': t.approval_desc, 'founder': t.founder,
        'exec_user': t.exec_user, 'status': t.get_status_display(),
        'start_time': dt.strftime(timezone.localtime(t.start_time),
                                  fmt) if t.status != 'no_run' else '未开始',
        'end_time': dt.strftime(timezone.localtime(t.end_time),
                                fmt) if t.status == 'finish' else '未完成',
        'cost_time': (t.end_time - t.start_time).total_seconds() if t.approval_status == 'Y' else '未完成',
        'recipient': t.recipient.name if t.recipient is not None else '启动人',
    }) for t in tasks]

    return JsonResponse(result, safe=False)


# @permission_required('om.can_approval_task', login_url='/om/no_permission/')
@login_required
def approval_task(request, task_id):
    settings.logger.info('%s %s' % (request.user.username, task_id))
    context = {'saved': request.method == 'POST', 'task_id': task_id}
    task = get_object_or_404(Task, pk=task_id)
    # if 'can_approval_task' not in get_perms(request.user, task):
    if not any([request.user.has_perm('om.can_approval_task'), request.user.has_perm('om.can_approval_task', task)]):
        return no_permission(request)
    if request.method == 'POST':
        task.approval(request.user.username, request.POST['result'], request.POST['reason'])
    return render(request, 'om/approval_task.html', context)


@login_required
def task_item_detail(request, task_job_id):
    settings.logger.info('%s %s' % (request.user.username, task_job_id))
    task_job = get_object_or_404(TaskJob, pk=task_job_id)
    return render(request, 'om/task_item_detail.html', {
        'tid': task_job_id,
        'ip_list_field': ['server_list'],
        'form': TaskItemForm(instance=task_job)
    })


@login_required
def task_server_detail_list(request, task_job_id):
    settings.logger.info(f'{request.user.username}, {task_job_id}')
    result = []
    for ip in str2arr(TaskJob.objects.get(pk=task_job_id).server_list, digit_check=False):
        cpt = Computer.objects.filter(ip=ip)
        if not cpt.exists():
            continue
        cpt = cpt.first()
        k = f'{ip}-{cpt.host}'
        info = {f'{ip}-{cpt.host}': []}
        for ent in cpt.entity.all():
            system = ent.system
            sys_name = f'{system.name}' if system.desc.strip() in ['', 'NA'] else f'{system.name}({system.desc})'
            info[k].append({'系统': sys_name, '实体': ent.name})
        result.append(info)
    return JsonResponse(result, safe=False)


@login_required
def valid_task_job_ip_list(request, task_job_id):
    settings.logger.info(f'{request.user.username}, {task_job_id}')
    result = {}
    ip_list = str2arr(TaskJob.objects.get(pk=task_job_id).server_list, digit_check=False)
    not_in_computers = set(ip_list) - set(Computer.objects.filter(ip__in=ip_list).values_list('ip', flat=True))
    not_in_salt_minions = [x for x in ip_list if not ip_in_salt_minion(x)]
    if len(not_in_computers) == 0 and len(not_in_salt_minions) == 0:
        return JsonResponse({'结果': '通过！'}, safe=False)
    if len(not_in_computers) > 0:
        result['未录入系统信息'] = list(not_in_computers)
    if len(not_in_salt_minions) > 0:
        result['salt未上线'] = [x for x in ip_list if not ip_in_salt_minion(x)]
    return JsonResponse(result, safe=False)


@login_required
def get_common_script_content(request, s_id):
    settings.logger.info('%s %s' % (request.user.username, s_id))
    sc = get_object_or_404(CommonScript, pk=s_id)
    return JsonResponse({'content': sc.content})


@login_required
def set_group_host(request, group_id):
    settings.logger.info('%s %s' % (request.user.username, group_id))
    group = get_object_or_404(JobGroup, pk=group_id)

    if not any([request.user.has_perm('om.change_jobgroup'), request.user.has_perm('om.change_jobgroup', group)]):
        return no_permission(request)

    if request.method == 'POST':
        server_list = [x['ip'] for x in json.loads(request.POST['server_list'])]
        if len(server_list) > 0:
            for job in [Job.objects.get(pk=x) for x in str2arr(group.job_list)]:
                job.server_list.clear()
                job.server_list.add(*[x for x in Computer.objects.filter(ip__in=server_list)])

        return render(request, 'om/close_this_layer.html', {'msg': '保存成功！'})
    return render(request, 'om/set_group_host.html')


@login_required
def modify_password(request, old_pwd, new_pwd):
    settings.logger.info(request.user.username)
    user = auth.authenticate(username=request.user.username, password=old_pwd)
    if user is not None and user.is_active:
        user.set_password(new_pwd)
        return JsonResponse({'result': '修改成功'})
    else:
        return JsonResponse({'result': '修改失败'})


@login_required
def chg_pwd(request):
    settings.logger.info(request.user.username)
    if request.method == 'POST':
        form = ChgPwdForm(request.POST)
        if form.is_valid():
            old_pwd = request.POST['old_pwd']
            user = auth.authenticate(username=request.user.username, password=old_pwd)
            if user is not None and user.is_active:
                user.set_password(request.POST['new_pwd'])
                user.save()
                return render(request, 'om/close_this_layer.html', {'msg': '修改成功！'})
            else:
                return render(request, 'om/chg_pwd.html', {'form': form, 'msg': '原始密码输入错误！'})
        else:
            return render(request, 'om/chg_pwd.html', {'form': form, 'msg': '两次输入密码不一致！'})
    else:
        form = ChgPwdForm()
        return render(request, 'om/chg_pwd.html', {'form': form})


@login_required
def unlock_win(request):
    settings.logger.info(request.user.username)
    return render(request, 'om/unlock_win.html')


@login_required
def select_server_list(request, job_id):
    settings.logger.info('%s %s' % (request.user.username, job_id))
    result = []
    selected_id_list = set([])
    if int(job_id) != -1:
        [selected_id_list.add(x['id']) for x in Job.objects.get(pk=job_id).server_list.values('id')]
    computer_list = {'label': '主机列表', 'children': []}
    computers = Computer.objects.filter(env=settings.OM_ENV) if settings.OM_ENV != 'PRD' else Computer.objects.all()
    for c in computers:
        option = {'label': str(c), 'value': c.id}
        if c.id in selected_id_list:
            option['selected'] = True
        computer_list['children'].append(option)
    result.append(computer_list)
    computer_group_list = {'label': '主机组列表', 'children': []}
    for cg in ComputerGroup.objects.filter(env=settings.OM_ENV):
        option = {'label': cg.name, 'value': 'group-{id}'.format(id=cg.id)}
        all_cp_list = set([x['id'] for x in cg.computer_list.values('id')])
        if all_cp_list.issubset(selected_id_list):
            option['selected'] = True
        computer_group_list['children'].append(option)
    result.append(computer_group_list)
    return JsonResponse({'server_list': result})


@login_required
def show_server(request):
    settings.logger.info(request.user.username)
    return render(request, 'om/show_server.html')


@login_required
def salt_status_api(request):
    settings.logger.info(request.user.username)
    search_fields = ['pk__icontains', 'name__icontains', 'host__icontains', 'sn__icontains', 'ip_list__icontains', 'status__icontains', 'env__icontains', 'os__icontains']
    minions, minion_count = get_paged_query(SaltMinion.objects.all(), search_fields, request)
    result = {'total': minion_count, 'rows': []}

    fmt = '%Y-%m-%d %H:%M:%S'
    [result['rows'].append({
        'id': x.id, 'name': x.name, 'host': x.host, 'ip_list': x.ip_list, 'sn': x.sn,
        'env': x.env, 'os': x.os, 'status': x.status,
        'update_time': dt.strftime(timezone.localtime(x.update_time), fmt)
    }) for x in minions]
    return JsonResponse(result, safe=False)


@login_required
def salt_status(request):
    settings.logger.info(request.user.username)
    return render(request, 'om/salt_status.html')


@login_required
def add_auto_task(request):
    settings.logger.info(request.user.username)

    perm = 'djcelery.add_periodictask'
    if not request.user.has_perm(perm):
        return HttpResponseRedirect("/om/no_permission/")

    if request.method == 'POST':
        tid = request.POST['task_base']
        try:
            if Task.objects.get(pk=tid).approval_status != 'Y':
                return render(request, 'om/close_this_layer.html', {'msg': '添加失败，请先对确保任务已审批通过！'})
        except Task.DoesNotExist as e:
            settings.logger.error(repr(e))
            return render(request, 'om/close_this_layer.html', {'msg': '任务已失效！'})
        p = PeriodicTask.objects.create(task='om.util.celery_auto_task')
        p.name = request.POST['name']
        p.args = '[{task_id}, "{user}"]'.format(task_id=tid, user='auto')
        p.enabled = request.POST.get('enabled', 'off') == 'on'
        task_type = request.POST['task_type']
        interval_val = request.POST['interval_val']
        interval_unit_type = request.POST['interval_unit_type']
        cron_val = request.POST['cron_val'].split(' ')
        expire_time = request.POST['expire_time']
        # IntervalSchedule, CrontabSchedule
        if task_type == 'interval':
            p.interval, _ = IntervalSchedule.objects.get_or_create(every=int(interval_val), period=interval_unit_type)
            p.crontab = None
        else:
            p.interval = None
            try:
                p.crontab, _ = CrontabSchedule.objects.get_or_create(
                    minute=cron_val[0], hour=cron_val[1], day_of_month=cron_val[2],
                    month_of_year=cron_val[3], day_of_week=cron_val[4]
                )
            except IndexError as _:
                return render(request, 'om/close_this_layer.html', {'msg': '周期控制器格式错误！'})
        if expire_time.strip() == '____-__-__ __:__:__':
            expire_time = ''
        p.expires = None if expire_time.strip() == '' else dt.strptime(expire_time, '%Y-%m-%d %H:%M:%S')
        p.founder = request.user.username
        p.last_modified_by = request.user.username
        p.save()
        return render(request, 'om/close_this_layer.html', {'msg': '保存成功！'})
    else:
        return render(request, 'om/add_auto_task.html',
                      {'task_list': Task.objects.all().order_by('-start_time'), 'task_id': '-1'})


@login_required
def delete_auto_task(request, task_id):
    settings.logger.info('%s %s' % (request.user.username, task_id))
    try:
        p = PeriodicTask.objects.get(pk=task_id)
        if p.locked:
            return JsonResponse({'result': 'N', 'msg': '不能删除锁定状态的任务！'})
        perm = 'djcelery.delete_periodictask'
        if not any([request.user.has_perm(perm), request.user.has_perm(perm, p)]):
            return JsonResponse({'result': 'N', 'msg': '没有删除权限'})
        p.delete()
    except PeriodicTask.DoesNotExist as e:
        settings.logger.error(repr(e))
        settings.logger.error(traceback.format_exc())
        return JsonResponse({'result': 'N', 'msg': '找不到改记录，无需删除！'})
    return JsonResponse({'result': 'Y', 'msg': '删除成功！'})


@login_required
def modify_auto_task(request, task_id):
    settings.logger.info('%s %s' % (request.user.username, task_id))
    p = get_object_or_404(PeriodicTask, id=task_id)
    perm = 'djcelery.change_periodictask'

    if not any([request.user.has_perm(perm), request.user.has_perm(perm, p)]):
        return no_permission(request)

    if not p.locked:
        return render(request, 'om/close_this_layer.html', {'msg': '请先锁定！'})

    if request.method == 'POST':
        p.name = request.POST['name']
        p.args = '[{task_id}, "{user}"]'.format(task_id=request.POST['task_base'], user='auto')
        p.enabled = request.POST.get('enabled', 'off') == 'on'
        task_type = request.POST['task_type']
        interval_val = request.POST['interval_val']
        interval_unit_type = request.POST['interval_unit_type']
        cron_val = request.POST['cron_val'].split(' ')
        expire_time = request.POST['expire_time']
        # IntervalSchedule, CrontabSchedule
        if task_type == 'interval':
            p.interval, _ = IntervalSchedule.objects.get_or_create(every=int(interval_val), period=interval_unit_type)
            p.crontab = None
        else:
            p.interval = None
            try:
                p.crontab, _ = CrontabSchedule.objects.get_or_create(
                    minute=cron_val[0], hour=cron_val[1], day_of_month=cron_val[2],
                    month_of_year=cron_val[3], day_of_week=cron_val[4]
                )
            except IndexError as _:
                return render(request, 'om/close_this_layer.html', {'msg': '周期控制器格式错误！'})
        if expire_time.strip() == '____-__-__ __:__:__':
            expire_time = ''
        p.expires = None if expire_time.strip() == '' else dt.strptime(expire_time, '%Y-%m-%d %H:%M:%S')
        p.last_modified_by = request.user.username
        p.save()
        return render(request, 'om/close_this_layer.html', {'msg': '保存成功！'})
    else:
        fmt = '%Y-%m-%d %H:%M:%S'
        task = task_from_args(p.args)
        return render(request, 'om/modify_auto_task.html', {
            'task_list': Task.objects.all().order_by('-start_time'),
            'id': p.id,
            'name': p.name,
            'type': '定时任务' if p.interval is None else '周期任务',
            'enabled': '是' if p.enabled else '否',
            'interval_val': '0' if p.interval is None else str(p.interval.every),
            'interval_unit': 'minutes' if p.interval is None else str(p.interval.period),
            'cron': '无' if p.crontab is None else str(p.crontab),
            'expires': '' if p.expires is None else dt.strftime(timezone.localtime(p.expires), fmt),
            'select_task_id': '-1' if task is None else task.id
        })


@login_required
def lock_auto_task(request, auto_task_id):
    settings.logger.info(f'{request.user.username}, {auto_task_id}')
    try:
        p = PeriodicTask.objects.get(pk=auto_task_id)
        if p.locked:
            return JsonResponse({'result': False, 'desc': '已锁定过，请刷新最新状态！'})
        else:
            p.last_modified_by = request.user.username
            p.locked = True
            p.save()
            return JsonResponse({'result': True})
    except PeriodicTask.DoesNotExist as e:
        settings.logger.error(repr(e))
        return JsonResponse({'result': False, 'desc': f'定时任务[{auto_task_id}]不存在！'})


@login_required
def unlock_auto_task(request, auto_task_id):
    settings.logger.info(f'{request.user.username}, {auto_task_id}')
    try:
        p = PeriodicTask.objects.get(pk=auto_task_id)
        if p.locked:
            if p.last_modified_by == request.user.username or request.user.is_superuser:
                p.last_modified_by = request.user.username
                p.locked = False
                p.save()
                return JsonResponse({'result': True})
            else:
                return JsonResponse({'result': False, 'desc': '请联系锁定人或管理员进行解锁！'})
        else:
            return JsonResponse({'result': False, 'desc': '不需要解锁，请刷新最新状态！'})
    except PeriodicTask.DoesNotExist as e:
        settings.logger.error(repr(e))
        return JsonResponse({'result': False, 'desc': f'定时任务[{auto_task_id}]不存在！'})


@login_required
def auto_task_is_locked(request, auto_task_id):
    settings.logger.info(f'{request.user.username}, {auto_task_id}')
    try:
        p = PeriodicTask.objects.get(pk=auto_task_id)
        return JsonResponse({'result': p.locked, 'lock_by': p.last_modified_by})
    except PeriodicTask.DoesNotExist as e:
        settings.logger.error(repr(e))
        return JsonResponse({'result': True, 'lock_by': 'NA'})


@login_required
def auto_task_list(request):
    settings.logger.info(request.user.username)
    search_fields = [
        'pk__icontains', 'name__icontains', 'founder__icontains', 'last_modified_by__icontains'
    ]
    auto_tasks, auto_task_count = get_paged_query(PeriodicTask.objects.filter(task='om.util.celery_auto_task'), search_fields, request)
    result = {'total': auto_task_count, 'rows': []}
    fmt = '%Y-%m-%d %H:%M:%S'
    for p in auto_tasks:
        task = task_from_args(p.args)
        task_info = '' if task is None else '{t_id}-{t_name}'.format(t_id=task.id, t_name=task.name)
        result['rows'].append({
            'id': p.id,
            'name': p.name,
            'args': task_info,
            'type': '定时任务' if p.interval is None else '周期任务',
            'enabled': '是' if p.enabled else '否',
            'interval': '无' if p.interval is None else str(p.interval),
            'crontab': '无' if p.crontab is None else str(p.crontab),
            'expires': '未设置' if p.expires is None else dt.strftime(timezone.localtime(p.expires), fmt),
            'founder': p.founder,
            'locked': p.locked,
            'last_modified_by': p.last_modified_by,
            'created_time': dt.strftime(timezone.localtime(p.created_time), fmt),
            'last_modified_time': dt.strftime(timezone.localtime(p.last_modified_time), fmt)
        })

    return JsonResponse(result, safe=False)


@login_required
def auto_task(request):
    settings.logger.info(request.user.username)
    return render(request, 'om/auto_task.html')


@login_required
def upload_file(request):
    settings.logger.info(request.user.username)
    if not request.user.has_perm('om.can_do_quick_file'):
        return no_permission(request)

    file_max_m = 20
    context = {'result': 'O', 'file_max_m': file_max_m}
    if request.method == 'POST':
        if settings.OM_ENV == 'PRD':
            file_upload = request.FILES.get('upload_file', None)
            if file_upload is None:
                context['result'] = 'N'
                context['msg'] = '没有文件需要上传！'
                return render(request, 'om/upload_file.html', context)
            if file_upload.size > file_max_m * 1024 * 1024:
                context['result'] = 'N'
                context['msg'] = '上传的文件不能大于{size}M！'.format(size=file_max_m)
                return render(request, 'om/upload_file.html', context)
            if ServerFile.objects.filter(name=file_upload.name).exists():
                context['result'] = 'N'
                context['msg'] = '{exists}文件重名！'.format(exists=file_upload.name)
                return render(request, 'om/upload_file.html', context)
            try:
                ftp = Ftp()
                ftp.upload_stream(file_upload.name, file_upload)
                ServerFile.objects.create(name=file_upload.name, founder=request.user.username,
                                          upload_time=timezone.now())
                ftp.quit()
                context['result'] = 'Y'
                context['msg'] = '{files}已上传成功！'.format(files=file_upload.name)
                return render(request, 'om/upload_file.html', context)
            except UnicodeEncodeError as e:
                settings.logger.error(repr(e))
                settings.logger.error(traceback.format_exc())
                context['result'] = 'N'
                context['msg'] = '上传失败，文件名不能包含中文！'
                return render(request, 'om/upload_file.html', context)
            except Exception as e:
                settings.logger.error(repr(e))
                settings.logger.error(traceback.format_exc())
                context['result'] = 'N'
                context['msg'] = '上传失败，请联系管理员确认原因！'
                return render(request, 'om/upload_file.html', context)
        context['result'] = 'N'
        context['msg'] = '仅生产环境支持上传文件！'
        return render(request, 'om/upload_file.html', context)
    else:
        return render(request, 'om/upload_file.html', context)


@login_required
def download_file(request, sf_id):
    settings.logger.info(request.user.username)
    try:
        sf = ServerFile.objects.get(pk=sf_id)
        perm = 'om.can_do_quick_file'
        if not any([request.user.has_perm(perm), request.user.has_perm(perm, sf)]):
            return no_permission(request)
        ftp = Ftp()
        response = HttpResponse()
        ftp.download_stream(sf.name, response)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = f'attachment;filename={sf.name}'
        ftp.quit()
        return response
    except ServerFile.DoesNotExist as e:
        settings.logger.error(repr(e))
        return JsonResponse({'result': 'N', 'desc': '该文件不存在！'})


@login_required
def get_server_file_list(request):
    settings.logger.info(request.user.username)
    search_fields = ['pk__icontains', 'name__icontains', 'founder__icontains', 'desc__icontains']
    server_files, server_files_count = get_paged_query(ServerFile.objects.all(), search_fields, request)
    result = {'total': server_files_count, 'rows': []}
    fmt = '%Y-%m-%d %H:%M:%S'
    [result['rows'].append({
        'id': f.id, 'name': f.name, 'founder': f.founder,
        'upload_time': dt.strftime(timezone.localtime(f.upload_time), fmt),
        'desc': f.desc
    }) for f in server_files]
    return JsonResponse(result, safe=False)


@login_required
def get_grains(request):
    settings.logger.info(request.user.username)
    return JsonResponse(get_agent_info(request.POST['agent_name']), safe=False)


@login_required
def admin_action(request, name):
    settings.logger.info('%s %s' % (request.user.username, name))
    minion = SaltMinion.objects.get(name=name, status='up')
    if not any([request.user.has_perm('om.can_exec_cmd'), request.user.has_perm('om.can_exec_cmd', minion)]):
        return no_permission(request)
    users = ExecUser.objects.all()
    if not any([request.user.has_perm('om.can_root'), request.user.has_perm('om.can_root', minion)]):
        users = users.exclude(name='root')
    return render(request, 'om/admin_action.html', {
        'minion': minion,
        'users': ['NA'] if minion.os == 'Windows' else list(users.values_list('name', flat=True)),
        'default_user': 'NA' if minion.os == 'Windows' else 'logarchive'
    })


@login_required
def set_flow_recipient(request, flow_id, mail_group_id):
    try:
        flow = Flow.objects.get(pk=flow_id)
        if not any([request.user.has_perm('om.change_flow'), request.user.has_perm('om.change_flow', flow)]):
            return JsonResponse({'result': 'N', 'msg': '没有删除权限'})
        flow.recipient = MailGroup.objects.get(pk=mail_group_id) if mail_group_id != '-1' else None
        flow.save()
    except Flow.DoesNotExist as e:
        settings.logger.error(repr(e))
        return JsonResponse({'result': 'N', 'desc': '作业流不存在！'})
    except MailGroup.DoesNotExist as e:
        settings.logger.error(repr(e))
        return JsonResponse({'result': 'N', 'desc': '邮件组不存在！'})
    return JsonResponse({'result': 'Y', 'desc': '设置成功！'})


# noinspection PyAttributeOutsideInit
class ComputerTaskView(AutoResponseView):
    def get(self, request, *args, **kwargs):
        self.widget = self.get_widget_or_404()
        self.term = kwargs.get('term', request.GET.get('term', ''))
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return JsonResponse({
            'results': [
                {
                    'text': self.widget.label_from_instance(obj),
                    'id': obj.pk,
                }
                for obj in context['object_list']
                ],
            'more': context['page_obj'].has_next()
        })

    def get_queryset(self):
        from om.util import get_task_computers_list
        """Get QuerySet from cached widget."""
        self.queryset = get_task_computers_list(self.request.user)
        return self.widget.filter_queryset(self.term, self.queryset)


@login_required
def get_mail_group_list(request):
    settings.logger.info(request.user.username)
    search_fields = ['pk__icontains', 'name__icontains', 'last_modified_by__icontains']
    mail_groups, mail_group_count = get_paged_query(MailGroup.objects.all(), search_fields, request)
    result = {'total': mail_group_count, 'rows': []}
    fmt = '%Y-%m-%d %H:%M:%S'
    [result['rows'].append({
        'id': m.id, 'name': m.name, 'users': m.users(),
        'last_modified_by': m.last_modified_by,
        'last_modified_time': dt.strftime(timezone.localtime(m.last_modified_time), fmt),
    }) for m in mail_groups]
    return JsonResponse(result, safe=False)


@login_required
def mail_group(request):
    settings.logger.info(request.user.username)
    return render(request, 'om/mail_group.html')


@login_required
def new_mail_group(request):
    settings.logger.info(request.user.username)
    close_layer = 'Y'
    if not request.user.has_perm('om.add_mailgroup'):
        return no_permission(request)
    if request.method == 'POST':
        request.POST._mutable = True
        request.POST['last_modified_by'] = request.user.username
        request.POST._mutable = False
        form = MailGroupForm(request.POST)
        if form.is_valid():
            form.save(commit=False)
            form.instance.last_modified_by = request.user.username
            form.save()
        else:
            close_layer = 'N'
    else:
        form = MailGroupForm()
        close_layer = 'N'
    return render(request, 'om/new_mail_group.html', {
        'form': form, 'mul_select': ['user_list'],
        'close_layer': close_layer
    })


@login_required
def edit_mail_group(request, mg_id):
    settings.logger.info(f'{request.user.username}, {mg_id}')
    close_layer = 'Y'
    mg = get_object_or_404(MailGroup, pk=mg_id)
    mg.last_modified_by = request.user.username
    if not any([request.user.has_perm('om.change_mailgroup'), request.user.has_perm('om.change_mailgroup', mg)]):
        return no_permission(request)
    if request.method == 'POST':
        form = MailGroupForm(data=request.POST, instance=mg)
        if form.is_valid():
            form.save()
        else:
            close_layer = 'N'
    else:
        close_layer = 'N'
        form = MailGroupForm(instance=mg)
    return render(request, 'om/new_mail_group.html', {
        'form': form, 'mul_select': ['user_list'],
        'close_layer': close_layer
    })


@login_required
def delete_mail_group(request, mg_id):
    settings.logger.info(f'{request.user.username}, {mg_id}')
    try:
        mg = MailGroup.objects.get(pk=mg_id)
        if not any([request.user.has_perm('om.delete_mailgroup'), request.user.has_perm('om.delete_mailgroup', mg)]):
            return JsonResponse({'result': 'N', 'desc': '没有删除权限，请联系管理员！'})
        mg.delete()
    except MailGroup.DoesNotExist as e:
        settings.logger.error(repr(e))
        return JsonResponse({'result': 'N', 'desc': '记录不存在，删除失败！'})
    return JsonResponse({'result': 'Y', 'desc': '删除成功！'})


@login_required
def computer_ping(request, cpt_id):
    settings.logger.info(f'{request.user.username}, {cpt_id}')
    if not request.user.is_superuser:
        return JsonResponse({'result': 'N', 'desc': '无此操作权限，请联系管理员！'})
    result = check_cpt_ping(cpt_id)
    return JsonResponse({'result': 'Y' if result else 'N', 'desc': '服务可用' if result else '检查失败'}, safe=False)


@login_required
def salt_minion_ping(request, minion_id):
    settings.logger.info(f'{request.user.username}, {minion_id}')
    if not request.user.is_superuser:
        return JsonResponse({'result': 'N', 'desc': '无此操作权限，请联系管理员！'})
    result = check_minion_ping(minion_id)
    return JsonResponse({'result': 'Y' if result else 'N', 'desc': '服务可用' if result else '检查失败'}, safe=False)


@login_required
def lock_flow(request, flow_id):
    settings.logger.info(f'{request.user.username}, {flow_id}')
    try:
        flow = Flow.objects.get(pk=flow_id)
        if flow.locked:
            return JsonResponse({'result': False, 'desc': '已锁定过，请刷新最新状态！'})
        else:
            flow.last_modified_by = request.user.username
            flow.locked = True
            flow.save()
            return JsonResponse({'result': True})
    except Flow.DoesNotExist as e:
        settings.logger.error(repr(e))
        return JsonResponse({'result': False, 'desc': f'作业流[{flow_id}]不存在！'})


@login_required
def unlock_flow(request, flow_id):
    settings.logger.info(f'{request.user.username}, {flow_id}')
    try:
        flow = Flow.objects.get(pk=flow_id)
        if flow.locked:
            if flow.last_modified_by == request.user.username or request.user.is_superuser:
                flow.last_modified_by = request.user.username
                flow.locked = False
                flow.save()
                return JsonResponse({'result': True})
            else:
                return JsonResponse({'result': False, 'desc': '请联系锁定人或管理员进行解锁！'})
        else:
            return JsonResponse({'result': False, 'desc': '不需要解锁，请刷新最新状态！'})
    except Flow.DoesNotExist as e:
        settings.logger.error(repr(e))
        return JsonResponse({'result': False, 'desc': f'作业流[{flow_id}]不存在！'})


@login_required
def flow_is_locked(request, flow_id):
    settings.logger.info(f'{request.user.username}, {flow_id}')
    try:
        flow = Flow.objects.get(pk=flow_id)
        return JsonResponse({'result': flow.locked, 'lock_by': flow.last_modified_by})
    except Flow.DoesNotExist as e:
        settings.logger.error(repr(e))
        return JsonResponse({'result': True, 'lock_by': 'NA'})


def diy_report_download(request):
    import time
    import csv
    from django.http import StreamingHttpResponse
    settings.logger.info(request.user.username)

    class Echo(object):
        @classmethod
        def write(cls, value):
            return value

    def read_iterator():
        for c in Computer.objects.select_related().only('host', 'entity'):
            yield [c.host, c.entities()]

    writer = csv.writer(Echo())
    time_stamp = int(time.mktime(timezone.now().timetuple()))
    response = StreamingHttpResponse((writer.writerow(row) for row in read_iterator()), content_type="text/csv")
    response['Content-Disposition'] = f'attachment;filename=info-{time_stamp}.csv'
    return response
