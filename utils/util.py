import socket
import struct
from om.proxy import Salt
from om.models import SaltMinion
from ActionSpace.settings import logger
from utils.models import Activity


def join_activity(username):
    return Activity.objects.filter(join=True, user__username=username).exists()


# noinspection PyCompatibility
def format_subnet(subnet_input):
    """
     转换为子网地址,并检验和输出正确的子网地址
     192.168.2.1 -> 192.168.2.1/255.255.255.255
     192.168.2.1/24 -> 192.168.2.0/255.255.255.0
     192.168.2.1/255.255.255.0 -> 192.168.2.0/255.255.255.0
    """
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
            struct.pack(
                "!I", struct.unpack(
                    "!I", socket.inet_aton(subnet_array[0])
                )[0] & struct.unpack(
                    "!I", socket.inet_aton(subnet_array[1])
                )[0])
        ) + "/" + subnet_array[1]
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
            self, source, target, port, use_nc=False,
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
        self.check_result = []

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
        logger.info(f"{ag_list}:{is_win}")
        return self.salt.file_trans(ag_list, self.check_script, f'{self.win_tmp if is_win else self.linux_tmp}/check_connect.py')

    def _nc_valid(self, ag_list, fail_code):
        if not self.use_nc:
            return False
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
            logger.info(f"{r}")
            if not r[0]:
                self.code = 5
                return

        # 检查nc是否有效，无效则传探测脚本到linux
        ag_list = self._names(self.source_linux) + self._names(self.target_linux)
        if not all([self.use_nc, self._nc_valid(ag_list, 6)]):
            if len(ag_list) > 0:
                r = self._trans(ag_list, False)
                if not r[0]:
                    self.code = 7
                    self.valid_nc = False
        else:
            self.valid_nc = True and self.use_nc

    @classmethod
    def _names(cls, ins):
        return list(ins.values_list('name', flat=True))

    def _check_peer_listen(self, target):
        py = self.win_py if target.env == 'Windows' else self.linux_py
        tmp_path = self.win_tmp if target.env == 'Windows' else self.linux_tmp
        r = self.salt.shell(target.name, f'{py} {tmp_path}/{self.check_script} {target.ip()} {self.port}')
        return all([r[0], list(set(r[1]['return'][0].values())) == ['True']])

    def _check_peer_connect(self, target, linux=True):
        ag_list = self._names(self.source_linux) if linux else self._names(self.source_win)
        if len(ag_list) > 0:
            if linux:
                if self.valid_nc:
                    cmd = f'[ -n "$(nc -z -w 1 {target.ip()} {self.port}|grep succeeded)" ] && echo True || echo False'
                else:
                    cmd = f'{self.linux_py} {self.linux_tmp}/{self.check_script} {target.ip()} {self.port}'
                r = self.salt.shell(ag_list, cmd)
                check_pass = any([not r[0], list(set(r[1]['return'][0].values())) == ['True']])
                self.check_result.append({
                    'from': ag_list,
                    'to': target.name,
                    'port': self.port,
                    'pass': check_pass,
                    'desc': self.CODE[0 if check_pass else 10]
                })
                return check_pass
            else:
                cmd = f'{self.win_py} {self.win_tmp}/{self.check_script} {target.ip()} {self.port}'
                r = self.salt.shell(ag_list, cmd)
                check_pass = any([not r[0], list(set(r[1]['return'][0].values())) == ['True']])
                self.check_result.append({
                    'from': ag_list,
                    'to': target.name,
                    'port': self.port,
                    'pass': check_pass,
                    'desc': self.CODE[0 if check_pass else 10]
                })
                return check_pass

    def check(self):
        self.trans_script()
        self.check_result = []
        for target in self.target:
            # 1、检测对端端口是否已开通，不通则放弃检查
            if not self._check_peer_listen(target):
                self.check_result.append({
                    'from': target.name,
                    'to': target.name,
                    'port': self.port,
                    'pass': False,
                    'desc': self.CODE[9]
                })
                continue

            # 2、从源端探测对端端口
            self._check_peer_connect(target, True)
            self._check_peer_connect(target, False)
        return self.check_result
