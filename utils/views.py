from django.shortcuts import render
from django.http import JsonResponse

from utils.models import Activity
from utils.util import format_subnet, ip_in_subnet, NET_TABLE


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
    return JsonResponse({'names': [x.user.last_name+x.user.first_name for x in act], 'guess': [x.guess for x in act]})


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
        'voted': Activity.objects.count()-not_voted.count(),
        'i_voted': user.exists() and user.first().voted
    }
    return render(request, 'utils/activity.html', context)
