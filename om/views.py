# coding=utf-8
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from models import Flow, JobGroup, Job
from form import JobForm, JobGroupForm, OrderedMultiSelect
import random
import socket
import struct
import simplejson


# Create your views here.
@login_required
def index(request):
    return render(request, 'om/index.html')


@login_required
def default_content(request):
    return render(request, 'om/home.html')


@login_required
def index_content(request):
    return render(request, 'om/home.html')


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
        'fields': [x for x in Flow._meta.fields if x.name != 'job_group_list']
    }
    return render(request, 'om/exec_flow.html', context)


@login_required
def new_flow(request):
    return render(request, 'om/new_flow.html')


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
                flow.job_group_list = ','.join(flow.job_group_list.split(',') + [unicode(group.id)])
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
            job_group.job_list = ','.join(job_group.job_list.split(',') + [unicode(job.id)])
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
    group = get_object_or_404(JobGroup, pk=group_id)
    joblist = group.job_list.split(',')
    joblist.remove(job_id)
    group.job_list = ','.join(joblist)
    group.save()
    return JsonResponse({'result': 'OK'})


@login_required
def del_group(request, group_id):
    get_object_or_404(JobGroup, pk=group_id).delete()
    return JsonResponse({'result': 'OK'})


@login_required
def edit_flow(request, flow_id):
    flow = get_object_or_404(Flow, pk=flow_id)
    group_id_list = flow.job_group_list.split(',')
    flow_has_invalid_group = False
    groups = []

    for group_id in group_id_list:
        if group_id.isdigit() and int(group_id) > 0 and JobGroup.objects.filter(pk=int(group_id)).exists():
            job_group = JobGroup.objects.get(pk=int(group_id))
            group_info = {'group': job_group, 'job_list': []}
            job_list = []
            job_id_list = job_group.job_list.split(',')
            group_has_invalid_job = False
            for job_id in job_id_list:
                if job_id.isdigit() and int(job_id) > 0 and Job.objects.filter(pk=int(job_id)).exists():
                    job_list.append(Job.objects.get(pk=int(job_id)))
                else:
                    group_has_invalid_job = True
                    job_id_list.remove(job_id)
            if group_has_invalid_job:
                job_group.job_list = ','.join(job_id_list)
                job_group.save()
            group_info['job_list'] = job_list
            groups.append(group_info)
        else:
            flow_has_invalid_group = True
            group_id_list.remove(group_id)
    if flow_has_invalid_group:
        flow.job_group_list = ','.join(group_id_list)
        flow.save()

    context = {
        'flow': flow,
        'groups': groups
    }
    return render(request, 'om/edit_flow.html', context)


@login_required
def save_edit_flow(request):
    result = ['FLOW_INIT', 'TASK_INIT']
    if request.method == 'POST' and request.POST.keys():
        info = simplejson.loads(request.POST.keys()[0])
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
                group_task_list = ','.join([x.split('_')[-1] for x in info[k]])
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
def action_detail(request):
    return render(request, 'om/action_detail.html')


@login_required
def choose_server(request):
    return render(request, 'om/choose_server.html')


RANDOM_IP_POOL = ['192.168.10.222/0']


def __get_random_ip():
    str_ip = RANDOM_IP_POOL[random.randint(0, len(RANDOM_IP_POOL) - 1)]
    str_ip_addr = str_ip.split('/')[0]
    str_ip_mask = str_ip.split('/')[1]
    ip_addr = struct.unpack('>I', socket.inet_aton(str_ip_addr))[0]
    mask = 0x0
    for i in range(31, 31 - int(str_ip_mask), -1):
        mask = mask | (1 << i)
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
    return JsonResponse([
        {
            'task_name': '检查REDIS状态',
            'run_user': '韦权祖',
            'task_status': '执行成功',
            'start_time': '2015-12-02 18:16:14',
            'end_time': '2015-12-02 18:12:02',
            'cost_time': '500',
        },
        {
            'task_name': '重启REDIS',
            'run_user': '韦权祖',
            'task_status': '执行成功',
            'start_time': '2015-12-02 18:16:14',
            'end_time': '2015-12-02 18:12:02',
            'cost_time': '500',
        },
        {
            'task_name': '检查DSP-CCS-ACTIVE状态',
            'run_user': '韦权祖',
            'task_status': '执行失败',
            'start_time': '2015-12-02 18:16:14',
            'end_time': '2015-12-02 18:12:02',
            'cost_time': '500',
        },
        {
            'task_name': '重启DSP-CCS-ACTIVE',
            'run_user': '韦权祖',
            'task_status': '执行成功',
            'start_time': '2015-12-02 18:16:14',
            'end_time': '2015-12-02 18:12:02',
            'cost_time': '500',
        },
    ], safe=False)
