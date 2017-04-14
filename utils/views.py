from functools import reduce
from ActionSpace.settings import logger
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from utils.models import Activity, CommonAddress, NetArea, NetInfo
from utils.util import format_subnet, ip_in_subnet, sh_zs
from utils.form import WallForm
import json
import re


# Create your views here.
@login_required
def picutil(request):
    return render(request, 'utils/picutil.html')


@login_required
def query_net_area(request):
    ip = request.POST['ip']
    for net_info in NetInfo.objects.all():
        if ip_in_subnet(ip, format_subnet(f'{net_info.ip}/{net_info.mask}')):
            result = f'网区：{net_info.region.area.name}，网段：{net_info.region.name}'
            return JsonResponse({'result': result})
    return JsonResponse({'result': '未知网段'})


@login_required
def net(request):
    return render(request, 'utils/net.html', {'net_area': NetArea.objects.all()})


@login_required
def activity_data(_):
    act = Activity.objects.filter(join=True).order_by('guess')
    return JsonResponse({'names': [x.user.last_name + x.user.first_name for x in act], 'guess': [x.guess for x in act]})


@login_required
def activity_vote(request):
    try:
        user = Activity.objects.get(user=request.user)
        user.vote(request.POST['guess'])
    except Activity.DoesNotExist as e:
        print(e)
    return JsonResponse({'result': 'Y'})


@login_required
def activity_status(request):
    joined_member = Activity.objects.filter(join=True)
    return JsonResponse({
        'joined_count': joined_member.count(), 'voted_count': joined_member.filter(voted=True).count()
    })


@login_required
def get_sh_zs(request):
    return JsonResponse({'result': sh_zs()})


@login_required
def activity(request):
    me = Activity.objects.filter(user=request.user, join=True)
    context = {
        'finished': not Activity.objects.filter(join=True, voted=False).exists(),
        'i_need_voted': me.exists() and not me.first().voted
    }
    return render(request, 'utils/activity.html', context)


@login_required
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


def common_address(request):
    return render(request, 'utils/common_address.html', {'objects': CommonAddress.objects.all()})
