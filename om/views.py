# coding=utf-8
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404,render
from models import Flow, JobGroup, Job
import random
import socket
import struct
import simplejson


# Create your views here.
def index(request):
    return render(request, 'om/index.html')


def default_content(request):
    return render(request, 'om/home.html')


def index_content(request):
    return render(request, 'om/home.html')


def quick_exec_script(request):
    return render(request, 'om/quick_exec_script.html')


def quick_upload_file(request):
    return render(request, 'om/quick_upload_file.html')


def exec_flow(request):
    context = {
        'flows': Flow.objects.all(),
        'fields': [x for x in Flow._meta.fields if x .name != 'job_group_list']
    }
    return render(request, 'om/exec_flow.html', context)


def new_flow(request):
    return render(request, 'om/new_flow.html')


def edit_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    context = {
        'job': job
    }
    return render(request, 'om/edit_job.html', context)


def edit_flow(request, flow_id):
    flow = Flow.objects.get(pk=flow_id)
    groups_objects = JobGroup.objects
    job_objects = Job.objects
    groups = []
    for group_id in flow.job_group_list.split(','):
        if group_id.isdigit() and int(group_id) > 0:
            job_group = groups_objects.get(pk=int(group_id))
            group_info = {'group': job_group, 'job_list': []}
            job_list = []
            for job_id in job_group.job_list.split(','):
                if job_id.isdigit() and int(job_id) > 0:
                    job_list.append(job_objects.get(pk=int(job_id)))
            group_info['job_list'] = job_list
            groups.append(group_info)
    context = {
        'flow': flow,
        'groups': groups
    }
    return render(request, 'om/edit_flow.html', context)


def save_edit_flow(request):
    result = ['FLOW_INIT','TASK_INIT']
    if request.method == 'POST' and request.POST.keys():
        info =simplejson.loads(request.POST.keys()[0])
        flow_sort = info['flow']
        if flow_sort:
            flow = Flow.objects.get(pk=int(info['id']))
            new_job_group_list = ','.join([x.replace('group_', '') for x in flow_sort])
            #update flow job_group_list
            if flow and flow.job_group_list != new_job_group_list:
                flow.job_group_list = new_job_group_list
                flow.save()
                result[0] = 'FLOW_SAVE'
            #update jobgroup tast_list
            task_change = False
            for k in flow_sort:
                group_task_list = ','.join([x.replace('task_', '') for x in info[k]])
                group = JobGroup.objects.get(pk=int(k.replace('group_', '')))
                if group and group.job_list != group_task_list:
                    group.job_list = group_task_list
                    group.save()
                    task_change = True
                if task_change:
                    result[1] = 'TASK_SAVE'
    return JsonResponse(result, safe=False)


def action_history(request):
    return render(request, 'om/action_history.html')


def action_detail(request):
    return render(request, 'om/action_detail.html')


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
