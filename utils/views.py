from functools import reduce
from django.shortcuts import render
from django.http import JsonResponse
from utils.models import Activity
from utils.util import format_subnet, ip_in_subnet, NET_TABLE
from utils.form import WallForm
import json
import re
from ActionSpace.settings import logger


# Create your views here.
def picutil(request):
    return render(request, 'utils/picutil.html')


def query_net_area(request):
    ip = request.POST['ip']
    for net_group in NET_TABLE.values():
        for net_chile, net_ip_list in net_group.items():
            if net_chile != 'name':
                for net_ip in net_ip_list:
                    if ip_in_subnet(ip, format_subnet(net_ip)):
                        result = '网区：{group}，网段：{area}'.format(group=net_group['name'], area=net_chile)
                        return JsonResponse({'result': result})
    return JsonResponse({'result': '未知网段'})


def net(request):
    return render(request, 'utils/net.html', {'net': NET_TABLE})


def activity_data(_):
    act = Activity.objects.filter(join=True).order_by('guess')
    return JsonResponse({'names': [x.user.last_name + x.user.first_name for x in act], 'guess': [x.guess for x in act]})


def activity_vote(request):
    try:
        user = Activity.objects.get(user=request.user)
        user.vote(request.POST['guess'])
    except Activity.DoesNotExist as e:
        print(e)
    return JsonResponse({'result': 'Y'})


def activity(request):
    user = Activity.objects.filter(user=request.user)
    not_voted = Activity.objects.filter(voted=False, join=True)
    all_voted = not not_voted.exists()
    if not user.exists():
        all_voted = True
    context = {
        'all_voted': all_voted,
        'count': Activity.objects.count(),
        'voted': Activity.objects.count() - not_voted.count(),
        'i_voted': user.exists() and user.first().voted
    }
    return render(request, 'utils/activity.html', context)


def make_firewall_table(request):
    if request.method == 'POST':
        form = WallForm(request.POST)
        if form.is_valid():
            try:
                def ft(c, k):
                    return "</br>".join(reduce(lambda x, y: x + y, [list(x.values_list(k, flat=True)) for x in c]))
                env = form.cleaned_data['env']
                data = json.loads(request.POST['exist_list'])
                s_target = "</br>".join([x.name for x in form.cleaned_data['source_entity']])
                s_computer = [e.computer_set.filter(env=env) for e in form.cleaned_data['source_entity']]
                s_host = ft(s_computer, 'host')
                s_ip = ft(s_computer, 'ip')
                t_target = "</br>".join([x.name for x in form.cleaned_data['target_entity']])
                t_computer = [e.computer_set.filter(env=env) for e in form.cleaned_data['target_entity']]
                t_host = ft(t_computer, 'host')
                t_ip = ft(t_computer, 'ip')
                port = "</br>".join(re.split(r'\W+', form.cleaned_data['port']))
                data.append({
                    's_entity': f"{s_target}",
                    's_host': f"{s_host}",
                    's_ip': f"{s_ip}",
                    't_entity': f"{t_target}",
                    't_host': f"{t_host}",
                    't_ip': f"{t_ip}",
                    'port': f"{port}",
                    'service': 'TCP',
                    'idle_time': '无',
                    'app_req': '无',
                    'valid_time': '长期',
                    'env': form.cleaned_data['env']
                })
                return render(request, 'utils/make_firewall.html', {
                    'data': data,
                    'form': form
                })
            except Exception as e:
                logger.error(repr(e))
                return render(request, 'utils/make_firewall.html', {'errors': form.errors, 'form': form})
        else:
            return render(request, 'utils/make_firewall.html', {'errors': form.errors, 'form': form})
    return render(request, 'utils/make_firewall.html', {'form': WallForm()})
