# coding: utf-8
import sys
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ActionSpace.settings")
django.setup()
from django.db import connection
from ast import literal_eval
from django.utils import timezone
import pytz
from om.models import CallLog
from django.contrib.auth.models import User

def last_count():
    result = 20
    if len(sys.argv) > 1 and sys.argv[1].isdecimal():
        result = sys.argv[1]
    return result

def get_ip(detail):
    try:
        ip_dict = literal_eval(detail)
    except Exception as e:
        ip_dict = None
    if ip_dict is None:
        ip = ''
    elif 'HTTP_X_REAL_IP' in ip_dict:
        ip = ip_dict['HTTP_X_REAL_IP']
    elif 'HTTP_X_FORWARDED_FOR' in ip_dict:
        ip = ip_dict['HTTP_X_FORWARDED_FOR']
    elif 'headers' in ip_dict:
        ip = [x[1].decode('unicode-escape') for x in ip_dict['headers'] if x[0] in [b'x-forwarded-for', b'x-real-ip']]
        ip = ','.join(set(ip))
    else:
        ip = ''
    return ip

if __name__ == '__main__':
    CallLog.objects.filter(user__in=User.objects.filter(username__in=['adminuser1', 'adminuser2'])).delete()
    cursor = connection.cursor()
    sql = f'select id, action, date_time,(select username from auth_user where id=user_id ) username, detail, type from (select * from om_calllog order by date_time desc) where rownum < {last_count()}'
    cursor.execute(sql)
    for id, action, date_time, username, detail, type in cursor.fetchall()[::-1]:
        print(f"{id}, {username:15s}, {get_ip(detail.read()):16s}, {timezone.localtime(date_time.replace(tzinfo=pytz.utc)).strftime('%Y-%m-%d %H:%M:%S')}, {type}, {action.split('/')[1:-1]}")
