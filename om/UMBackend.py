# coding=utf-8
from django.contrib.auth.models import User
from ActionSpace.settings import OM_ENV
import requests
import json


class UMBackend(object):
    def __init__(self):
        self.is_prd = OM_ENV == 'PRD'
        if self.is_prd:
            self.url = 'prd_umauthurl'
        else:
            self.url = 'uat_umauthurl'

    def authenticate(self, username='', password=''):
        if '' in [username, password]:
            return None
        user = None
        un = username
        if not self.is_prd and username == 'uat_test_user':
            un = 'UAT_TEST_USER'
        r = requests.post(self.url, data=json.dumps({'user': un, 'pwd': password}))
        r = r.json()
        if r.get('err', -1) == 0:
            user, created = User.objects.get_or_create(username=un)
            if user:
                user.set_password(password)
                user.email = '{un}@pingan.com.cn'.format(un=username)
                if 'data' in r:
                    data = r['data']
                    if 'name' in data and len(data['name']) > 0:
                        um_name = data['name']
                        user.last_name = um_name[0]
                        user.first_name = um_name[1:]
                user.save()
        # 这里不判断用户是否active，留给login函数判断然会返回给页面
        return user  # if self.user_can_authenticate(user) else None

    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
            return user if self.user_can_authenticate(user) else None
        except User.DoesNotExist:
            return None

    @staticmethod
    def user_can_authenticate(user):
        is_active = getattr(user, 'is_active', None)
        return is_active or is_active is None
