# coding=utf-8
import json

from django.http import HttpResponseRedirect
# from guardian.shortcuts import get_perms

from om.util import *
from django.contrib.auth.decorators import login_required
# from guardian.decorators import permission_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from om.form import JobForm, JobGroupForm, FlowForm, TaskItemForm
from om.models import Flow, JobGroup, Job, Task, TaskFlow, TaskJobGroup, TaskJob, Computer, System
from datetime import datetime as dt


# Create your views here.
@login_required
def index(request):
    return render(request, 'om/index.html', {'user': request.user})


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
        'server_count': Computer.objects.count()
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
        'fields': [x for x in Flow._meta.fields if x.name not in ['job_group_list', 'is_quick_flow']]
    }
    return render(request, 'om/exec_flow.html', context)


@login_required
def create_task(request, flow_id, job_id):
    if flow_id == -1 and job_id != -1:  # flow不存在， job存在说明是快速执行任务来的
        job = get_object_or_404(Job, pk=job_id)
        group = JobGroup.objects.create(name='临时组', job_list=str(job.id))
        group.save()
        flow = Flow.objects.create(is_quick_flow=True, job_group_list=str(group.id))
        flow.save()
    else:
        flow = get_object_or_404(Flow, pk=flow_id)

    task = Task.objects.create(name=flow.name, exec_user=request.user.username, approval_time=timezone.now())
    t_flow = TaskFlow.objects.create(name=flow.name, flow_id=flow.pk, task=task)
    for group_id in str2arr(flow.job_group_list):
        group = JobGroup.objects.get(pk=group_id)
        t_group = TaskJobGroup.objects.create(name=group.name, group_id=group.pk, flow=t_flow)
        for job_id in str2arr(group.job_list):
            job = Job.objects.get(pk=job_id)
            server_ip_list = ','.join([x.ip for x in job.server_list.all()])
            TaskJob.objects.create(
                name=job.name, job_id=job.pk, group=t_group, job_type=job.job_type,
                script_type=job.script_type, script_content=job.script_content,
                begin_time=timezone.now(), end_time=timezone.now(), status='no_run',
                pause_when_finish=job.pause_when_finish, script_param=job.script_param,
                server_list=server_ip_list,
                pause_finish_tip=job.pause_finish_tip, exec_output=''
            )

    task.save()
    return JsonResponse({'result': 'N', 'desc': '任务已创建！'})


def clone_task(task):
    t_flow = task.taskflow_set.first()
    new_t_task = Task.objects.create(name=task.name, exec_user=task.exec_user, approval_time=timezone.now())
    new_t_flow = TaskFlow.objects.create(name=t_flow.name, flow_id=t_flow.flow_id, task=new_t_task)
    for task_group in t_flow.taskjobgroup_set.all():
        t_group = TaskJobGroup.objects.create(name=task_group.name, group_id=task_group.group_id, flow=new_t_flow)
        for task_job in task_group.taskjob_set.all():
            TaskJob.objects.create(
                name=task_job.name, job_id=task_job.job_id, group=t_group, job_type=task_job.job_type,
                script_type=task_job.script_type, script_content=task_job.script_content,
                begin_time=timezone.now(), end_time=timezone.now(), status='no_run',
                pause_when_finish=task_job.pause_when_finish, script_param=task_job.script_param,
                server_list=task_job.server_list, pause_finish_tip=task_job.pause_finish_tip,
                exec_output=''
            )
    new_t_task.save()
    return new_t_task


@login_required
def exec_task(request, task_id):
    try:
        task = Task.objects.get(pk=task_id)
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
            task.exec_user = request.user.username
            task.save()
            return JsonResponse({'result': 'Y', 'desc': '任务[{tid}]已发送到后台执行。'.format(tid=task.id)})
        else:
            return JsonResponse({'result': 'N', 'desc': '任务[{tid}]不包含任何作业流。'.format(tid=task.id)})
    except Task.DoesNotExist as e:
        print(e)
        return JsonResponse({'result': 'N', 'desc': '任务[{tid}]不存在！'.format(tid=task_id)})


@login_required
def redo_create_task(request, task_id):
    for task in Task.objects.filter(pk=task_id):
        new_task = clone_task(task)
        new_task.exec_user = request.user.username
        new_task.save()
        return JsonResponse({'result': 'Y', 'desc': 'ID为[{tid}]的任务已创建。'.format(tid=new_task.id)})
    return JsonResponse({'result': 'N', 'desc': 'ID为[{tid}]任务不存在！'.format(tid=task_id)})


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
        'normal_check_list': ['server_list'],
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
        'normal_check_list': ['server_list'],
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
        info = json.loads(list(request.POST.keys())[0])
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
    task = get_object_or_404(Task, pk=task_id)
    return render(request, 'om/action_detail.html', {'task': task.id})


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


@login_required
def choose_server_result(_):
    server_list = []
    for computer in Computer.objects.all():
        server_list.append({
            'server_ip': computer.ip,
            'server_hostname': computer.host,
            'server_status': computer.installed_agent,
        })
    return JsonResponse(server_list, safe=False)


@login_required
def get_server_list(_):
    server_list = []
    for system in System.objects.all():
        for entity in system.entity_set.all():
            for computer in entity.computer_set.all():
                server_list.append({
                    'system': system.name,
                    'env': computer.env,
                    'entity': entity.name,
                    'server_ip': computer.ip,
                    'server_hostname': computer.host,
                    'server_status': computer.installed_agent,
                })
    return JsonResponse(server_list, safe=False)


@login_required
def get_action_history_list(_):
    result = []
    fmt = '%Y-%m-%d %H:%M:%S'
    for t in Task.objects.order_by('-id'):
        result.append({
            'task_id': t.id, 'task_name': t.name, 'approval_status': t.get_approval_status_display(),
            'approver': t.approver, 'approval_desc': t.approval_desc,
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
    context = {'saved': request.method == 'POST', 'task_id': task_id}
    task = get_object_or_404(Task, pk=task_id)
    # if 'can_approval_task' not in get_perms(request.user, task):
    if not request.user.has_perm('om.can_approval_task') and not request.user.has_perm('om.can_approval_task', task):
        return HttpResponseRedirect("/om/no_permission/")
    if request.method == 'POST':
        task.approval(request.user.username, request.POST['result'], request.POST['reason'])
    return render(request, 'om/approval_task.html', context)


@login_required
def task_item_detail(request, task_job_id):
    task_job = get_object_or_404(TaskJob, pk=task_job_id)
    return render(request, 'om/task_item_detail.html', {'form': TaskItemForm(instance=task_job)})


def no_permission(request):
    return render(request, 'om/403.html')
