from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from switch.models import *
from om.util import get_paged_query
import datetime
import logging
import time
import xlwt


logger = logging.getLogger('switch')


# Create your views here.
@login_required
def get_machine_list(request, search_id):
    logger.info(request.user.username)
    search_fields = [
        'mac_hex__icontains', 'mac_decimal__icontains', 'switch__ip__icontains',
        'net_face__name__icontains', 'minion__name__icontains', 'desc__icontains'
    ]
    q = Machine.objects.select_related('minion').select_related('net_face').select_related('switch').filter(search__id=search_id)
    machines, machine_count = get_paged_query(q, search_fields, request)
    result = {'total': machine_count, 'rows': []}
    [result['rows'].append({
            'ip': 'NA' if m.minion is None else m.minion.name,
            'mac_hex': m.mac_hex,
            'entity_name': m.entity_name().split(','),
            'switch_ip': m.switch.ip,
            'net_face': 'NA' if m.net_face is None else m.net_face.name
        }) for m in machines]
    return JsonResponse(result, safe=False)


@login_required
def index(request):
    logger.info(request.user.username)
    select = Search.objects.all()
    context = {
        'search_list': Search.objects.all(),
    }
    if select.count() > 0:
        context['current_select'] = select.first().id
    return render(request, 'switch/index.html', context)


@login_required
def export_excel(request, search_id):
    logger.info(request.user.username)
    style_heading = xlwt.easyxf(
        """
            font:
                name Arial,
                colour_index white,
                bold on,
                height 0xA0;
            align:
                wrap off,
                vert center,
                horiz center;
            pattern:
                pattern solid,
                fore-colour 0x19;
            borders:
                left THIN,
                right THIN,
                top THIN,
                bottom THIN;
            """
    )

    style_body = xlwt.easyxf(
        """
            font:
                name Arial,
                bold off,
                height 0XA0;
            align:
                wrap on,
                vert center,
                horiz left;
            borders:
                left THIN,
                right THIN,
                top THIN,
                bottom THIN;
            """
    )

    fmts = [
        'M/D/YY',
        'D-MMM-YY',
        'D-MMM',
        'MMM-YY',
        'h:mm AM/PM',
        'h:mm:ss AM/PM',
        'h:mm',
        'h:mm:ss',
        'M/D/YY h:mm',
        'mm:ss',
        '[h]:mm:ss',
        'mm:ss.0',
    ]

    style_body.num_format_str = fmts[0]

    wb = xlwt.Workbook(encoding='utf-8')
    w = wb.add_sheet('交换机主机信息')
    w.write(0, 0, "主机", style_heading)
    w.col(0).width = 256 * 20
    w.write(0, 1, "MAC地址", style_heading)
    w.col(1).width = 256 * 20
    w.write(0, 2, "逻辑实体", style_heading)
    w.col(2).width = 256 * 60
    w.write(0, 3, "交换机IP", style_heading)
    w.col(3).width = 256 * 20
    w.write(0, 4, "网口", style_heading)
    w.col(4).width = 256 * 20
    start = time.clock()
    for i, m in enumerate(Machine.objects.select_related('minion').select_related('net_face').select_related('switch').filter(search__id=search_id)):
        w.write(i+1, 0, 'NA' if m.minion is None else m.minion.name, style_body)
        w.write(i+1, 1, m.mac_hex, style_body)
        w.write(i+1, 2, m.entity_name(), style_body)
        w.write(i+1, 3, m.switch.ip, style_body)
        w.write(i+1, 4, 'NA' if m.net_face is None else m.net_face.name, style_body)
    end = time.clock()
    print('export_excel time is:{t}'.format(t=end - start))
    response = HttpResponse()
    response['Content-Disposition'] = 'attachment;filename=switch-{search}-{tm}.xls'.format(
        search=search_id, tm=int(time.mktime(datetime.datetime.now().timetuple())))
    wb.save(response)
    return response
