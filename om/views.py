# coding=utf-8
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from models import Flow
import random
import socket
import struct


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
        'fields': Flow._meta.fields
    }
    return render(request, 'om/exec_flow.html', context)


def new_flow(request):
    return render(request, 'om/new_flow.html')


def edit_job(request):
    return render(request, 'om/edit_job.html')


def edit_flow(request):
    return render(request, 'om/edit_flow.html')


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
