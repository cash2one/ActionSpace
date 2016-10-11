# coding=utf-8
import random
import socket
import struct
import json
from om.util import *
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from om.form import JobForm, JobGroupForm, FlowForm
from om.models import Flow, JobGroup, Job, Task, TaskFlow, TaskJobGroup, TaskJob
from datetime import datetime


# Create your views here.
@login_required
def index(request):
    return render(request, 'om/index.html')


@login_required
def default_content(request):
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
    }
    return render(request, 'om/home.html', context)


@login_required
def index_content(request):
    return default_content(request)


@login_required
def quick_exec_script(request):
    return render(request, 'om/quick_exec_script.html')


@login_required
def quick_upload_file(request):
    return render(request, 'om/quick_upload_file.html')


@login_required
def exec_flow(request):
    context = {
        'flows': Flow.objects.all(),
        'fields': [x for x in Flow._meta.fields if x.name not in ['job_group_list', 'is_quick_flow']]
    }
    return render(request, 'om/exec_flow.html', context)


def send_task_to_exec(user_name, task):
    result = {'result': 'Y', 'task': '-1', 'desc': ''}
    if task.taskflow_set.count() > 0:
        # exec_task(task.id, user_name)
        res = exec_task.delay(task.id, user_name)
        task.async_result = res.id
        task.save()
        result['task'] = task.id
    else:
        result['result'] = 'N'
        result['task'] = '-1'
        result['desc'] = '作业流没有执行内容'
    return result


def new_task(username, flow_id, job_id):
    if flow_id == -1 and job_id != -1:  # flow不存在， job存在说明是快速执行任务来的
        job = get_object_or_404(Job, pk=job_id)
        group = JobGroup.objects.create(name='临时组', job_list=str(job.id))
        group.save()
        flow = Flow.objects.create(is_quick_flow=True, job_group_list=str(group.id))
        flow.save()
    else:
        flow = get_object_or_404(Flow, pk=flow_id)

    task = Task.objects.create(name=flow.name, exec_user=username)
    t_flow = TaskFlow.objects.create(name=flow.name, flow_id=flow.pk, task=task)

    for group_id in str2arr(flow.job_group_list):
        group = JobGroup.objects.get(pk=group_id)
        t_group = TaskJobGroup.objects.create(name=group.name, group_id=group.pk, flow=t_flow)
        for job_id in str2arr(group.job_list):
            job = Job.objects.get(pk=job_id)
            TaskJob.objects.create(
                name=job.name, job_id=job.pk, group=t_group, job_type=job.job_type,
                script_type=job.script_type, script_content=job.script_content,
                begin_time=timezone.now(), end_time=timezone.now(), status='no_run',
                pause_when_finish=job.pause_when_finish,
                pause_finish_tip=job.pause_finish_tip, exec_output=''
            )

    task.save()
    return task


def clone_task(tid):
    task = Task.objects.get(pk=tid)
    t_flow = task.taskflow_set.first()
    new_t_task = Task.objects.create(name=task.name, exec_user=task.exec_user)
    new_t_flow = TaskFlow.objects.create(name=t_flow.name, flow_id=t_flow.flow_id, task=new_t_task)
    for task_group in t_flow.taskjobgroup_set.all():
        t_group = TaskJobGroup.objects.create(name=task_group.name, group_id=task_group.group_id, flow=new_t_flow)
        for task_job in task_group.taskjob_set.all():
            TaskJob.objects.create(
                name=task_job.name, job_id=task_job.job_id, group=t_group, job_type=task_job.job_type,
                script_type=task_job.script_type, script_content=task_job.script_content,
                begin_time=timezone.now(), end_time=timezone.now(), status='no_run',
                pause_when_finish=task_job.pause_when_finish,
                pause_finish_tip=task_job.pause_finish_tip, exec_output=''
            )
    new_t_task.save()
    return new_t_task


@login_required
def go_exec(request, flow_id, job_id):
    return JsonResponse(send_task_to_exec(
        request.user.username, new_task(request.user.username, flow_id, job_id)))


@login_required
def redo_exec(request, task_id):
    return JsonResponse(send_task_to_exec(request.user.username, clone_task(task_id)))


@login_required
def task_status(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    context = {
        'can_get_result': False,
        'result': ''
    }
    if task.async_result != '':
        context['can_get_result'] = True
        context['result'] = get_task_result(task.async_result)
    return render(request, 'om/task_status.html', context)


@login_required
def get_flow_list(_):
    fmt = '%Y年%m月%d日 %H:%M:%S'
    return JsonResponse(
        [{
             'id': x.id,
             'name': x.name,
             'founder': x.founder,
             'last_modified_by': x.last_modified_by,
             'created_time': datetime.strftime(timezone.localtime(x.created_time), fmt),
             'last_modified_time': datetime.strftime(timezone.localtime(x.last_modified_time), fmt),
             'desc': x.desc
         } for x in Flow.objects.all() if not x.is_quick_flow
         ],
        safe=False)


@login_required
def flow_clone(request, flow_id):
    flow = Flow.objects.get(pk=flow_id)
    flow.pk = None
    flow.save()
    return JsonResponse({'result': 'OK', 'id': flow.pk})


@login_required
def flow_delete(_, flow_id):
    Flow.objects.get(pk=flow_id).delete()
    return JsonResponse({'result': 'OK'})


@login_required
def new_flow(request):
    save = {
        'saved': False,
        'result': False,
        'error_msg': 'NA'
    }
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
    save = {
        'saved': False,
        'result': False,
        'error_msg': 'NA'
    }
    if request.method == 'POST':
        save['saved'] = True
        group_form = JobGroupForm(data=request.POST)
        try:
            if group_form.is_valid():
                group = group_form.save_form(request, create=True)
                flow = get_object_or_404(Flow, pk=flow_id)
                flow.last_modified_by = request.user.username
                flow.job_group_list = ','.join(str2arr(flow.job_group_list) + [str(group.id)])
                flow.save()
                save['result'] = True
        except Exception as e:
            save['result'] = False
            save['error_msg'] = e.message
    else:
        group_form = JobGroupForm()

    context = {
        'form': group_form,
        'check_field_list': ['pause_when_finish', 'pause_when_error'],
        'disable_field_list': ['job_list_comma_sep'],
        'save': save,
    }
    return render(request, 'om/edit_group.html', context)


@login_required
def edit_group(request, group_id):
    group = get_object_or_404(JobGroup, pk=group_id)
    save = {
        'saved': False,
        'result': False,
        'error_msg': 'NA'
    }
    if request.method == 'POST':
        save['saved'] = True
        group_form = JobGroupForm(data=request.POST, instance=group)
        try:
            if group_form.is_valid():
                group_form.save_form(request)
                save['result'] = True
        except Exception as e:
            save['result'] = False
            save['error_msg'] = e.message
    else:
        group_form = JobGroupForm(instance=group)

    context = {
        'form': group_form,
        'check_field_list': ['pause_when_finish', 'pause_when_error'],
        'disable_field_list': ['job_list_comma_sep'],
        'save': save,
    }
    return render(request, 'om/edit_group.html', context)


@login_required
def new_job(request, job_group_id):
    save = {
        'saved': False,
        'result': False,
        'error_msg': 'NA'
    }
    if request.method == 'POST':
        save['saved'] = True
        job_form = JobForm(data=request.POST)
        try:
            job = job_form.save_form(request, commit=False, create=True)
            job_group = get_object_or_404(JobGroup, pk=job_group_id)
            job_group.last_modified_by = request.user.username
            job_group.job_list = ','.join(str2arr(job_group.job_list) + [str(job.id)])
            job_group.save()
            save['result'] = True
        except Exception as e:
            save['result'] = False
            save['error_msg'] = e.message
    else:
        job_form = JobForm()
        job_form.last_modified_by = request.user

    context = {
        'form': job_form,
        'check_field_list': ['pause_when_finish', 'pause_when_error', 'file_from_local'],
        'save': save,
    }
    return render(request, 'om/edit_job.html', context)


@login_required
def edit_job(request, job_id):
    save = {
        'saved': False,
        'result': False,
        'error_msg': 'NA'
    }
    job = get_object_or_404(Job, pk=job_id)
    job.last_modified_by = request.user
    if request.method == 'POST':
        save['saved'] = True
        job_form = JobForm(data=request.POST, instance=job)
        # noinspection PyBroadException
        try:
            if job_form.is_valid():
                job_form.save_form(request)
                save['result'] = True
        except Exception as e:
            save['result'] = False
            save['error_msg'] = e.message
    else:
        job_form = JobForm(instance=job)
    context = {
        'form': job_form,
        'check_field_list': ['pause_when_finish', 'pause_when_error', 'file_from_local'],
        'disable_field_list': ['last_modified_by', 'founder'],
        'save': save,
    }
    return render(request, 'om/edit_job.html', context)


@login_required
def del_job_in_group(request, group_id, job_id):
    context = {'result': 'OK'}
    try:
        group = JobGroup.objects.get(pk=group_id)
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
    context = {'result': 'OK'}
    try:
        flow = Flow.objects.get(pk=flow_id)
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
    flow = get_object_or_404(Flow, pk=flow_id).validate_job_group_list()
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
    result = ['FLOW_INIT', 'TASK_INIT']
    if request.method == 'POST' and request.POST.keys():
        info = json.loads(request.POST.keys()[0])
        flow_sort = info['flow']
        if flow_sort:
            flow = Flow.objects.get(pk=int(info['id']))
            new_job_group_list = ','.join([x.replace('group_', '') for x in flow_sort])
            # update flow job_group_list
            if flow and flow.job_group_list != new_job_group_list:
                flow.job_group_list = new_job_group_list
                flow.save()
                result[0] = 'FLOW_SAVE'
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
                    result[1] = 'TASK_SAVE'
    return JsonResponse(result, safe=False)


@login_required
def action_history(request):
    return render(request, 'om/action_history.html')


@login_required
def action_detail(request, task_id):
    return render(request, 'om/action_detail.html', {'task': get_object_or_404(Task, pk=task_id).id})


@login_required
def detail_content(request, task_id, first):
    if first == '0':
        TaskChange(task_id).wait_change()
    task = get_object_or_404(Task, pk=task_id)
    cost_time = 0
    if task.status == 'finish':
        cost_time = (task.end_time - task.start_time).total_seconds()
    context = {
        'task': task,
        'flow'
        'cost_time': cost_time
    }
    return render(request, 'om/detail_content.html', context)


@login_required
def confirm_task(request, task_id, flow_id, group_id, job_id):
    TaskConfirm('%s-%s-%s-%s' % (task_id, flow_id, group_id, job_id)).send_confirm()
    return JsonResponse({'result': 'OK'})


@login_required
def get_task_status(request, task_id):
    t = get_object_or_404(Task, pk=task_id)
    return JsonResponse({'status': t.status})


@login_required
def choose_server(request):
    return render(request, 'om/choose_server.html')


RANDOM_IP_POOL = ['192.168.10.222/0']


def __get_random_ip():
    str_ip = RANDOM_IP_POOL[random.randint(0, len(RANDOM_IP_POOL) - 1)]
    str_ip_addr = str2arr(str_ip, '/', False)[0]
    str_ip_mask = str2arr(str_ip, '/', False)[1]
    ip_addr = struct.unpack('>I', socket.inet_aton(str_ip_addr))[0]
    mask = 0x0
    for i in range(31, 31 - int(str_ip_mask), -1):
        mask |= 1 << i
    ip_addr_min = ip_addr & (mask & 0xffffffff)
    ip_addr_max = ip_addr | (~mask & 0xffffffff)
    return str(socket.inet_ntoa(
        struct.pack('>I', random.randint(ip_addr_min, ip_addr_max))))


@login_required
def choose_server_result(_):
    status = ['Agent正常', 'Agent不正常']
    server_list = []
    for i in range(50):
        server_list.append({
            'server_ip': __get_random_ip(),
            'server_hostname': __get_random_ip() + '-' + str(i),
            'server_status': status[random.randint(0, len(status) - 1)],
        })
    return JsonResponse(server_list, safe=False)


@login_required
def get_server_list(_):
    system_list = ['SODS-CORE', 'SACRM-MIC', 'SAMPMS-CORE', 'SRDM-CORE']
    env_list = ['uat', 'prd']
    status = ['Agent正常', 'Agent不正常']
    server_list = []
    for i in range(3000):
        server_list.append({
            'system': system_list[random.randint(0, len(system_list) - 1)],
            'env': env_list[random.randint(0, len(env_list) - 1)],
            'entity': system_list[random.randint(0, len(system_list) - 1)] + '-' + str(i),
            'server_ip': __get_random_ip(),
            'server_hostname': __get_random_ip() + '-' + str(i),
            'server_status': status[random.randint(0, len(status) - 1)],
        })
    return JsonResponse(server_list, safe=False)


@login_required
def get_action_history_list(_):
    result = []
    fmt = '%Y年%m月%d日 %H:%M:%S'
    for t in Task.objects.order_by('-id'):
        result.append({
            'task_id': t.id, 'task_name': t.name,
            'run_user': t.exec_user, 'task_status': t.get_status_display(),
            'start_time': datetime.strftime(timezone.localtime(t.start_time),
                                            fmt) if t.status != 'no_run' else '还没开始',
            'end_time': datetime.strftime(timezone.localtime(t.end_time),
                                          fmt) if t.status == 'finish' else '没有跑完',
            'cost_time': (t.end_time - t.start_time).total_seconds(),
        })

    return JsonResponse(result, safe=False)
