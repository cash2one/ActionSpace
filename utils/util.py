import socket
import struct
from collections import OrderedDict
from om.proxy import Salt
from om.models import SaltMinion

# noinspection PyCompatibility
NET_TABLE = OrderedDict([
    ('area_one', OrderedDict([
        ('name', '业务一区'),
        ('SF网段', [
            '192.168.252.0/24', '192.168.253.0/24', '10.17.134.0/24',
            '10.17.135.0/24', '10.17.142.0/24', '10.17.144.0/24',
            '10.17.145.0/24', '10.17.198.0/24', '10.17.130.0/24'
        ]),
        ('WEBII', ['10.17.168.0/24', '10.17.143.0/24', '10.17.166.0/23', '26.2.16.0/23']),
        ('DB', ['26.2.0.0/23']),
        ('报盘', ['26.2.2.0/23']),
        ('APP', ['26.2.4.0/23']),
        ('APP_F5私网', ['192.167.0.0/24', '192.167.8.0/22']),
        ('WEBII_F5私网', ['192.167.1.0/24', '192.167.16.0/22']),
        ('APP_F5_VIP', ['10.17.142.0/24']),
        ('WEBII_F5_VIP', ['10.17.143.0/24'])
    ])),
    ('area_two', OrderedDict([
        ('name', '业务二区'),
        ('SF', ['10.17.128.0/24', '10.17.132.0/24']),
        ('WEBII', ['26.4.16.0/23']),
        ('DB', ['26.4.0.0/23']),
        ('APP', ['26.4.4.0/23']),
        ('APP_F5私网', ['192.167.24.0/22']),
        ('WEBII_F5私网', ['192.167.32.0/22']),
        ('APP_F5_VIP', ['10.17.168.0/22', '26.4.32.0/22']),
        ('WEBII_F5_VIP', ['192.168.252.0/22', '26.4.36.0/22'])
    ])),
    ('area_other', OrderedDict([
        ('name', '其他区'),
        ('大数据', ['26.6.0.0/23']),
        ('citrix', ['10.17.146.0/24']),
        ('堡垒机', ['10.17.183.0/24']),
        ('网管（应用监控）', ['10.17.162.0/24']),
        ('ISA', ['10.17.138.0/24']),
        ('合作伙伴', ['192.167.3.0/24', '192.167.4.0/24']),
        ('合作伙伴-NAT', ['10.17.136.0/24']),
        ('互联网-交易', ['10.17.188.0/24', '10.17.189.0/24']),
        ('互联网-交易F5', ['172.17.17.0/23', '172.17.6.0/24']),
        ('互联网-非交易', ['10.17.187.0/24']),
        ('互联网-非交易F5', ['172.17.20.0/24']),
        ('NAS-SF', ['172.19.12.0/24', '172.19.13.0/24', *['172.20.{:d}.0/24'.format(x) for x in range(8, 15 + 1)]]),
        ('NAS-WEBII', ['172.19.14.0/24', *['172.20.{:d}.0/24'.format(x) for x in range(16, 23 + 1)]]),
        ('NAS-DMZ', ['172.19.16.0/24', *['172.20.{:d}.0/24'.format(x) for x in range(24, 31 + 1)]]),
        ('NAS-citrix', ['172.19.18.0/24', *['172.20.{:d}.0/24'.format(x) for x in range(32, 39 + 1)]]),
        ('ILO网段', [
            *['172.19.{:d}.0/24'.format(x) for x in range(8, 12+1)],
            *['172.19.{:d}.0/24'.format(x) for x in range(16, 32+1)]
        ])
    ])),
    ('area_pilot', OrderedDict([
        ('name', '领航网段'),
        ('服务器-网关', ['192.168.5.200']),
        ('服务器', ['192.168.5.0/24']),
        ('开发PC机-网关', ['192.168.7.200']),
        ('开发PC机', ['192.168.6.0/24', '192.168.7.0/24']),
        ('纽约', ['192.168.20.0/24']),
        ('芝加哥', ['192.168.25.0/24']),
    ])),
])

'''
 转换为子网地址,并检验和输出正确的子网地址
 192.168.2.1 -> 192.168.2.1/255.255.255.255
 192.168.2.1/24 -> 192.168.2.0/255.255.255.0
 192.168.2.1/255.255.255.0 -> 192.168.2.0/255.255.255.0
 '''


def format_subnet(subnet_input):
    # 如果输入的ip，将掩码加上后输出
    if subnet_input.find("/") == -1:
        return subnet_input + "/255.255.255.255"
    else:
        # 如果输入的是短掩码，则转换为长掩码
        subnet = subnet_input.split("/")
        if len(subnet[1]) < 3:
            mask_num = int(subnet[1])
            last_mask_num = mask_num % 8
            last_mask_str = ""
            for i in range(last_mask_num):
                last_mask_str += "1"
            if len(last_mask_str) < 8:
                for i in range(8 - len(last_mask_str)):
                    last_mask_str += "0"
            last_mask_str = str(int(last_mask_str, 2))
            if mask_num // 8 == 0:
                subnet = subnet[0] + "/" + last_mask_str + "0.0.0"
            elif mask_num // 8 == 1:
                subnet = subnet[0] + "/255." + last_mask_str + ".0.0"
            elif mask_num // 8 == 2:
                subnet = subnet[0] + "/255.255." + last_mask_str + ".0"
            elif mask_num // 8 == 3:
                subnet = subnet[0] + "/255.255.255." + last_mask_str
            elif mask_num // 8 == 4:
                subnet = subnet[0] + "/255.255.255.255"
            subnet_input = subnet

            # 计算出正确的子网地址并输出
        subnet_array = subnet_input.split("/")
        subnet_true = socket.inet_ntoa(
            struct.pack("!I", struct.unpack("!I", socket.inet_aton(subnet_array[0]))[0] &
                        struct.unpack("!I", socket.inet_aton(subnet_array[1]))[0])) + "/" + subnet_array[1]
        return subnet_true


# 判断ip是否属于某个网段
def ip_in_subnet(ip, subnet):
    subnet = format_subnet(str(subnet))
    subnet_array = subnet.split("/")
    ip = format_subnet(ip + "/" + subnet_array[1])
    return ip == subnet


class CheckFireWall(object):
    CODE = {
        0: 'OK',
        1: 'Invalid port',
        2: 'Invalid source',
        3: 'Invalid target',
        4: 'All env of computer must be the same in one batch',
        5: 'Trans test script to windows fail',
        6: 'No nc in linux',
        7: 'Trans test script to linux fail',
        8: 'Check peer port fail',
        9: 'Peer port is not listening',
        10: 'The port is unreachable[linux]',
        11: 'The port is unreachable[windows]'
    }

    def __init__(
            self, source, target, port, use_nc=True,
            win_py='C:/salt/bin/python.exe',
            win_tmp='C:/Windows/TEMP',
            linux_py='python',
            linux_tmp='/tmp',
            check_script='check_connect.py'
    ):
        self.win_py = win_py
        self.win_tmp = win_tmp
        self.linux_py = linux_py
        self.linux_tmp = linux_tmp
        self.check_script = check_script
        self.source = source
        self.target = target
        self.port = port
        self.use_nc = use_nc
        self.code = 0
        self.salt = None
        self.env = None
        self.source_win = None
        self.source_linux = None
        self.target_win = None
        self.target_linux = None
        self.valid_nc = False
        self.check_result = {}
        self.check_port()
        self.check_agent_name()
        self.check_env()

    def status(self, code=None):
        return self.CODE[self.code if code is None else code]

    @classmethod
    def _valid_agent(cls, name):
        if isinstance(name, list):
            ag_list = SaltMinion.objects.filter(name__in=name)
            return len(name) == ag_list.count(), ag_list
        else:
            ag_list = SaltMinion.objects.filter(name=name)
            return ag_list.exists(), ag_list

    def check_port(self):
        if self.code != 0:
            return
        if not all([isinstance(self.port, (str, int)), str(self.port).isdigit(), 1 <= int(self.port) <= 65535]):
            self.code = 1

    def check_agent_name(self):
        if self.code != 0:
            return
        result = self._valid_agent(self.source)
        if not result[0]:
            self.code = 2
        else:
            self.source = result[1]
        result = self._valid_agent(self.target)
        if not result[0]:
            self.code = 3
        else:
            self.target = result[1]
        if self.code == 0:
            self.source_win = self.source.filter(os='Windows')
            self.source_linux = self.source.exclude(os='Windows')
            self.target_win = self.target.filter(os='Windows')
            self.target_linux = self.target.exclude(os='Windows')

    def check_env(self):
        if self.code != 0:
            return
        all_env = set(list(self.source.values_list('env', flat=True)) + list(self.target.values_list('env', flat=True)))
        if len(all_env) != 1:
            self.code = 4
        if self.code == 0:
            self.env = list(all_env)[0]
            self.salt = Salt(self.env)

    def _trans(self, ag_list, is_win):
        return self.salt.file_trans(ag_list, self.check_script, f'{self.win_tmp if is_win else self.linux_tmp}/check_connect.py')

    def _nc_valid(self, ag_list, fail_code):
        r = self.salt.shell(ag_list, 'which nc > /dev/null 2>&1;echo $?')
        if not r[0]:
            self.code = fail_code
            return False
        r_list = list(set(r[1]['return'][0].values()))
        return any([len(r_list) == 0, r_list[0] == '0'])

    def trans_script(self):
        if self.code != 0:
            return
        # 将探测脚本传到windows
        ag_list = self._names(self.source_win) + self._names(self.target_win)
        if len(ag_list) > 0:
            r = self._trans(ag_list, True)
            if not r[0]:
                self.code = 5
                return

        # 检查nc是否有效，无效则传探测脚本到linux
        ag_list = self._names(self.source_linux) + self._names(self.target_linux)
        if not any([
            not self.use_nc,  # 关闭nc检查
            not all([self.use_nc, self._nc_valid(ag_list, 6)])]  # nc开启但无效
        ):
            if len(ag_list) > 0:
                r = self._trans(ag_list, False)
                if not r[0]:
                    self.code = 7
        else:
            self.valid_nc = True

    @classmethod
    def _names(cls, ins):
        return list(ins.values_list('name', flat=True))

    def _check_peer_listen(self, target):
        py = self.win_py if target.env == 'Windows' else self.linux_py
        tmp_path = self.win_tmp if target.env == 'Windows' else self.linux_tmp
        r = self.salt.shell(target.name, f'{py} {tmp_path}/{self.check_script} {target.ip()} {self.port}')
        if not all([r[0], list(set(r[1]['return'][0].values())) == ['True']]):
            self.check_result[target.name]['peer_listen'] = 9
        return self.check_result[target.name]['peer_listen'] == 0

    def _check_peer_connect(self, target, linux=True):
        ag_list = self._names(self.source_linux) if linux else self._names(self.source_win)
        if len(ag_list) > 0:
            if linux:
                if self.valid_nc:
                    cmd = f'[ -n "$(nc -z -w 1 {target.ip()} {self.port}|grep succeeded)" ] && echo True || echo False'
                else:
                    cmd = f'{self.linux_py} {self.linux_tmp}/{self.check_script} {target.ip()} {self.port}'
                r = self.salt.shell(ag_list, cmd)
                self.check_result[target.name]['linux']['result'] = r[1]['return'][0]
                if not any([not r[0], list(set(r[1]['return'][0].values())) == ['True']]):
                    self.check_result[target.name]['linux']['code'] = 10
            else:
                cmd = f'{self.win_py} {self.win_tmp}/{self.check_script} {target.ip()} {self.port}'
                r = self.salt.shell(ag_list, cmd)
                print(r)
                self.check_result[target.name]['windows']['result'] = r[1]['return'][0]
                if not any([not r[0], list(set(r[1]['return'][0].values())) == ['True']]):
                    self.check_result[target.name]['windows']['code'] = 11

    def check(self):
        self.trans_script()
        for target in self.target:
            # 1、检测对端端口是否已开通
            self.check_result[target.name] = {
                'peer_listen': 0,
                'windows': {
                    'code': 0,
                    'result': None
                },
                'linux': {
                    'code': 0,
                    'result': None
                }
            }
            if not self._check_peer_listen(target):
                continue

            # 2、从源端探测对端端口
            self._check_peer_connect(target, True)
            self._check_peer_connect(target, False)
        return self.check_result
