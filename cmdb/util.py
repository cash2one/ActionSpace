# coding=utf-8
from om.proxy import Salt
from cmdb.models import Action
import requests


class CmdbApi(object):
    ERR_ID = -200
    NO_ID = -1
    CP_OS_ID = 25
    CP_HD_ID = 40

    def __init__(self):
        self.url_base = 'http://26.8.0.11:8080/balantflow/restservices/'
        self.last_error = ''

    @classmethod
    def get_env_name(cls, env):
        # 生产环境(PRD)，测试环境(UAT/QA)，开发环境(DEV)，开发自测(FAT)，温备环境(LDR)，灾备环境(DR)，仿真环境
        if env == 'PRD':
            return '生产环境(PRD)'
        elif env == 'UAT':
            return '测试环境(UAT/QA)'
        elif env == 'FAT':
            return '开发自测(FAT)'

    def send(self, api, post=True, data=None):
        url = self.url_base + api
        send_data = {} if data is None else data
        r = requests.post(url, json=send_data) if post else requests.get(url, params=send_data)
        if r.status_code == 200:
            return True, r.json()
        else:
            return False, {'code': r.status_code}

    def exist_trans(self, ci_id, ent_id):
        result, back = self.send('TransactionQueryRestApi', data={'ciId': ci_id, 'ciEntityId': ent_id, 'token': 0})
        assert result, '执行报错'
        return len(back['Return']) > 0

    def process_salt_grains(self, info, env):
        self.last_error = ''
        if not self.process_os(info, env):
            return False
        if True:
            return
        if not self.process_hardware(info, env):
            return False

    def process_os(self, info, env):
        os_id = self.get_cp_os_id(info['localhost'])
        if os_id == CmdbApi.ERR_ID:  # 执行报错
            print('exec error')
            return False
        elif os_id == CmdbApi.NO_ID:  # 对象不存在
            print('create new')
            return self.create_os_trans(None, info, env, True)
        else:  # 对象存在
            if self.exist_trans(CmdbApi.CP_OS_ID, os_id):  # 存在事务了，先不更新，等人工确定
                print(f'trans exist, ent id:{os_id}')
                return True
            else:  # 不存在事务， 这里新建一个事务
                print('create trans')
                return self.create_os_trans(os_id, info, env)

    def process_hardware(self, info, env):
        self.create_or_update_hardware(self.get_cp_hd_id(info['serialnumber']), {})

    def get_cp_os_id(self, hostname):
        return self.get_ent_id(CmdbApi.CP_OS_ID, {'label': 'OS名称', 'attrValue': hostname})

    def get_cp_hd_id(self, sn):
        return self.get_ent_id(CmdbApi.CP_HD_ID, {'label': '序列号', 'attrValue': sn})

    def get_ent_id(self, ci_id, condition):
        result, back = self.send(
            'ciEntityListByAttrlabelRestComponentApi',
            data={'ciId': ci_id, 'filterArray': [condition]}
        )
        if not result:
            self.last_error = '发送消息失败'
            return CmdbApi.ERR_ID
        if back['Status'] != 'OK':
            self.last_error = '接口返回状态不为OK'
            return CmdbApi.ERR_ID
        count = len(back['Return'])
        if count > 1:
            self.last_error = '对象不唯'
            return CmdbApi.ERR_ID
        if count == 0:
            self.last_error = '对象不存在'
            return CmdbApi.NO_ID
        return back['Return'][0]['id']

    def create_os_trans(self, os_id, info, env, commit=False):
        print('create_os_trans')
        data = {
            'ciId': CmdbApi.CP_OS_ID, 'saveMode': 1 if commit else 0,
            'editor': 'ADMIN',
            'attr_OS名称': info['localhost'],
            'attr_CPU核数': info['num_cpus'],
            'attr_OS状态': '建设中',
            'attr_环境': self.get_env_name(env)
        }
        if os_id is not None:
            data['ciEntityId'] = os_id
        print(data)
        return self.send('ciEntitySaveRestComponentApi', data=data)

    def create_or_update_hardware(self, sn, data):
        print(self.url_base, sn, data)


def update_computer(update_time, action_id, callback=None):
    # update_time放在参数里是为了在flower里看到
    # callback允许为空，这样方便手工调用

    def send(content):
        callback.msg(content) if callback else print(content)

    # action = Action.objects.get(pk=action_id)
    # if action.status == 'running':
    #     send('有任务正在执行，请等待执行完成！')
    #     return

    # action.status = 'running'
    print(update_time)
    api = CmdbApi()
    for env in ['PRD', 'UAT']:
        salt = Salt(env)
        check, back = salt.grains('*', ['localhost', 'num_cpus'])
        if check:
            for _, info in back['return'][0].items():
                process_result = api.process_salt_grains(info, env)
                if not process_result:
                    send(api.last_error)
                    # break  # 如果有失败则至二级返回，不再进行后面的批次
        else:
            send(f'获取grains失败')
        # action.status = 'success'
        # action.save()
        return True
