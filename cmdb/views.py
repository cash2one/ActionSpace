from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime as dt
from cmdb.models import Action


# Create your views here.
@login_required
def index(request):
    return render(request, 'cmdb/index.html')


@login_required
def get_action_list(request):
    result = []
    if request.user.is_superuser:
        fmt = '%Y-%m-%d %H:%M:%S'
        result = [{
            'id': x.id,
            'name': x.name,
            'founder': x.founder,
            'last_modified_by': x.last_modified_by,
            'created_time': dt.strftime(timezone.localtime(x.created_time), fmt),
            'last_modified_time': dt.strftime(timezone.localtime(x.last_modified_time), fmt),
            'status': x.get_status_display(),
            'async_result': x.async_result,
            'desc': x.desc
        } for x in Action.objects.all()]
    return JsonResponse(result, safe=False)

