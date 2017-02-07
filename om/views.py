# coding=utf-8
from django.contrib import auth
from django.http import HttpResponseRedirect
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
from om.form import JobForm, JobGroupForm, FlowForm, TaskItemForm, ChgPwdForm
from om.models import *
from djcelery.models import PeriodicTask, IntervalSchedule, CrontabSchedule
from datetime import datetime as dt
from ActionSpace import settings
from django.db import connection
from om.ftputil import Ftp
import json
import time


# Create your views here.
@login_required
def index(request):
    settings.logger.info(request.user.username)
    #  host_ora = {
    #      'UAT': {'notebook': 'http://10.25.167.89:8888/note/tree', 'flower': 'http://10.25.167.89:5555/'},
    #      'PRD': {'notebook': 'http://26.4.4.78:8081/note/tree', 'flower': 'http://26.4.4.78:8082/'}
    #  }
    host_nginx = {
        'UAT': {
            'notebook': 'http://stg-om.paic.com.cn/note/',
            'flower': 'http://stg-om.paic.com.cn/flower/',
            'redis': 'http://stg-om.paic.com.cn/redis/'
        },
        'PRD': {
            'notebook': 'http://om.paic.com.cn/note/',
            'flower': 'http://om.paic.com.cn/flower/',
            'redis': 'http://om.paic.com.cn/redis/'
        }
    }
    # noinspection PyShadowingNames
    from django.contrib.auth.models import Group as UG
    is_internal = UG.objects.get(name='应用服务二组').user_set.filter(username=request.user.username).exists()
    return render(request, 'om/index.html', {
        'user': request.user, 'host': host_nginx[settings.OM_ENV],
        'is_internal': is_internal or request.user.is_superuser
    })


@login_required
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
def index_content(request):
    settings.logger.info(request.user.username)
    return default_content(request)


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
            server_list = [x['server_ip'] for x in json.loads(request.POST['server_list'])]
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
        server_list = [x['server_ip'] for x in json.loads(request.POST['server_list'])]
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

    task = make_task(request.user.username, flow_id, job_id)
    return JsonResponse({'result': 'Y', 'desc': '任务已创建,ID={id}！'.format(id=task.id)})


@login_required
def exec_task(request, task_id):
    settings.logger.info('%s %s' % (request.user.username, task_id))

    try:
        task = Task.objects.get(pk=task_id)
        if not any([request.user.has_perm('om.can_exec_approved_task'), request.user.has_perm('om.can_exec_approved_task', task)]):
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
    return JsonResponse(
        [{
             'id': x.id,
             'name': x.name,
             'founder': x.founder,
             'last_modified_by': x.last_modified_by,
             'created_time': dt.strftime(timezone.localtime(x.created_time), fmt),
             'last_modified_time': dt.strftime(timezone.localtime(x.last_modified_time), fmt),
             'desc': x.desc
         } for x in Flow.objects.order_by('-id') if not x.is_quick_flow
         ],
        safe=False)


@login_required
def flow_clone(request, flow_id):
    settings.logger.info('%s %s' % (request.user.username, flow_id))
    flow = Flow.objects.get(pk=flow_id)
    if not any([request.user.has_perm('om.add_flow'), request.user.has_perm('om.add_flow', flow)]):
        return JsonResponse({'result': 'N', 'desc': '没有权限，请联系管理员！'})

    now_time = timezone.now()
    timestamp = int(time.mktime(now_time.timetuple()))
    cloned_flow = Flow.objects.create()
    cloned_flow.name = '{ts}_{name}'.format(ts=timestamp, name=flow.name)
    cloned_flow.founder = request.user.username
    cloned_flow.last_modified_by = request.user.username
    cloned_flow.created_time = now_time
    cloned_flow.last_modified_time = now_time
    cloned_flow.is_quick_flow = False
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

    flow.validate_job_group_list()
    context = {'flow': flow, 'groups': []}
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
    for c in Computer.objects.exclude(sys='linux'):
        server_list.append({
            'ip': c.ip,
            'host': c.host,
            'sys': c.sys,
            'env': c.env,
            'installed_agent': '是' if c.installed_agent else '否'
        })
    return JsonResponse(server_list, safe=False)


@login_required
def get_server_list(request):
    settings.logger.info(request.user.username)
    server_list = []
    use_raw_sql = True
    if use_raw_sql:
        cursor = connection.cursor()
        # noinspection SqlDialectInspection
        if settings.OM_ENV == 'UAT':
            # noinspection SqlDialectInspection
            sql = 'select s.name,c.env, e.name, c.ip, c.host,c.sys,c.agent_name,c.installed_agent from om_system s, om_computer c,om_entity e,' \
                  ' om_computer_entity ce where e.system_id = s.id and e.id = ce.entity_id and c.id = ce.computer_id and ' \
                  'c.env = \'{env}\''.format(env=settings.OM_ENV)
        else:
            # noinspection SqlDialectInspection
            sql = 'select s.name,c.env, e.name, c.ip, c.host,c.sys,c.agent_name,c.installed_agent from om_system s, om_computer c,om_entity e,' \
                  ' om_computer_entity ce where e.system_id = s.id and e.id = ce.entity_id and c.id = ce.computer_id'
        cursor.execute(sql)

        for system, env, entity, server_ip, server_hostname, sys, agent_name, installed_agent in cursor.fetchall():
            server_list.append({
                'system': system,
                'env': env,
                'entity': entity,
                'sys': sys,
                'installed_agent': '是' if installed_agent else '否',
                'agent_name': agent_name,
                'server_ip': server_ip,
                'server_hostname': server_hostname
            })
    else:
        info = Computer.objects.prefetch_related('entity__system').select_related()
        for computer in info:
            entity_set = computer.entity.all()
            for entity in entity_set:
                system = entity.system
                server_list.append({
                    'system': system.name,
                    'env': computer.env,
                    'entity': entity.name,
                    'server_ip': computer.ip,
                    'server_hostname': computer.host
                })
    return JsonResponse(server_list, safe=False)


@login_required
def get_action_history_list(request):
    settings.logger.info(request.user.username)
    result = []
    fmt = '%Y-%m-%d %H:%M:%S'
    for t in Task.objects.order_by('-start_time'):
        result.append({
            'task_id': t.id, 'task_name': t.name, 'approval_status': t.get_approval_status_display(),
            'approver': t.approver, 'approval_desc': t.approval_desc, 'founder': t.founder,
            'run_user': t.exec_user, 'task_status': t.get_status_display(),
            'start_time': dt.strftime(timezone.localtime(t.start_time),
                                      fmt) if t.status != 'no_run' else '未开始',
            'end_time': dt.strftime(timezone.localtime(t.end_time),
                                    fmt) if t.status == 'finish' else '未完成',
            'cost_time': (t.end_time - t.start_time).total_seconds() if t.approval_status == 'Y' else '未完成',
        })

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
    return render(request, 'om/task_item_detail.html', {'form': TaskItemForm(instance=task_job)})


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
        server_list = [x['server_ip'] for x in json.loads(request.POST['server_list'])]
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
    result = []
    env_map = {'PRD': '生产环境', 'UAT': '测试环境', 'FAT': '开发环境'}
    fmt = '%Y-%m-%d %H:%M:%S'
    [result.append({
        'name': x.name, 'status': x.status, 'env': env_map[x.env],
        'update_time': dt.strftime(timezone.localtime(x.update_time), fmt)
    }) for x in SaltMinion.objects.filter(env=settings.OM_ENV)]
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
        p = PeriodicTask.objects.create(task='om.util.celery_auto_task')
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
        p.save()
        return render(request, 'om/close_this_layer.html', {'msg': '保存成功！'})
    else:
        return render(request, 'om/add_auto_task.html', {'task_list': Task.objects.all().order_by('-start_time'), 'task_id': '-1'})


@login_required
def delete_auto_task(request, task_id):
    settings.logger.info('%s %s' % (request.user.username, task_id))
    try:
        p = PeriodicTask.objects.get(pk=task_id)
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
def auto_task_list(request):
    settings.logger.info(request.user.username)
    result = []
    fmt = '%Y-%m-%d %H:%M:%S'
    for p in PeriodicTask.objects.filter(task='om.util.celery_auto_task'):
        task = task_from_args(p.args)
        task_info = '' if task is None else '{t_id}-{t_name}'.format(t_id=task.id, t_name=task.name)
        result.append({
            'id': p.id,
            'name': p.name,
            'task_info': task_info,
            'type': '定时任务' if p.interval is None else '周期任务',
            'enabled': '是' if p.enabled else '否',
            'interval': '无' if p.interval is None else str(p.interval),
            'cron': '无' if p.crontab is None else str(p.crontab),
            'expires': '未设置' if p.expires is None else dt.strftime(timezone.localtime(p.expires), fmt)
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
                ServerFile.objects.create(name=file_upload.name, founder=request.user.username, upload_time=timezone.now())
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
def get_server_file_list(request):
    settings.logger.info(request.user.username)
    result = []
    fmt = '%Y-%m-%d %H:%M:%S'
    for f in ServerFile.objects.all():
        result.append({
            'name': f.name,
            'founder': f.founder,
            'upload_time': dt.strftime(timezone.localtime(f.upload_time), fmt),
            'desc': f.desc
        })
    return JsonResponse(result, safe=False)


@login_required
def get_grains(request):
    settings.logger.info(request.user.username)
    return JsonResponse(get_agent_info(request.POST['agent_name']), safe=False)
