# coding=utf-8
from celery import shared_task
from om.proxy import Salt
from cmdb.models import Action
import requests
import math


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

    def process_salt_grains(self, info, env):
        self.last_error = ''
        if not self.process_os(info, env):
            return False
        if not self.process_hardware(info, env):
            return False
        # mem_total = info['mem_total']
        # cpu_model = info['cpu_model']
        # num_cpus = info['num_cpus']
        # bios_version = info['biosversion']

    def process_os(self, info, env):
        os_id = self.get_os_id(info['localhost'])
        if os_id == CmdbApi.ERR_ID:
            return False
        data = {"ciId": CmdbApi.CP_OS_ID}
        self.create_or_update_os(data)

    def process_hardware(self, info, env):
        self.create_or_update_hardware(self.get_hardware_id(info['serialnumber']), {})

    def get_os_id(self, hostname):
        result, back = self.send(
            'ciEntityListByAttrlabelRestComponentApi',
            data={'ciId': CmdbApi.CP_OS_ID, 'filterArray': [{'label': 'OS名称', 'attrValue': hostname}]}
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
        return back['Return'][0]['ciId']

    def create_or_update_os(self, data):
        print(self.url_base, data)

    def get_hardware_id(self, sn):
        print(self.url_base, sn)
        return 1

    def create_or_update_hardware(self, sn, data):
        print(self.url_base, sn, data)


@shared_task
def update_computer(update_time, action_id, callback=None):
    # update_time放在参数里是为了在flower里看到
    # callback允许为空，这样方便手工调用

    def send(content):
        callback.msg(content) if callback else print(content)

    action = Action.objects.get(pk=action_id)
    if action.status == 'running':
        send('有任务正在执行，请等待执行完成！')
        return

    action.status = 'running'
    print(update_time)
    for env in ['PRD', 'UAT']:
        salt = Salt(env)
        ping_check, back = salt.ping('*')
        if not ping_check:
            send('ping 失败')
            action.status = 'fail'
            action.save()
            return False
        else:
            ag_list = back['return'][0].keys()

        # 分批处理，50一批
        count = len(ag_list)
        batch_count = 50
        api = CmdbApi()
        for batch in range(int(math.ceil(count/batch_count))):
            offset = batch * batch_count
            batch_list = ag_list[offset: min((offset+batch_count), count-1)]
            check, back = salt.grains(batch_list)
            if check:
                send(f'开始处理完成第{batch}批。')
                for info in back['return'][0].keys():
                    process_result = api.process_salt_grains(info, env)
                    if not process_result:
                        send(api.last_error)
                        break  # 如果有失败则至二级返回，不再进行后面的批次
                send(f'结束处理完成第{batch}批。')
            else:
                send(f'获取grains失败:{batch_list}')
        action.status = 'success'
        action.save()
        return True
