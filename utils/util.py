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


def check_by_script(salt, agent_list, target_ip, target_port, py_path, tmp_path):
    result, _ = salt.file_trans(agent_list, 'check_connect.py', f'{tmp_path}/check_connect.py')
    assert result, 'Can not be checked'
    result, back = salt.shell(agent_list, f'{py_path} %tmp%/check_connect.py {target_ip} {target_port}')
    assert result, 'Unable to execute command to check'
    test_result = list(set(back['return'][0].values()))
    return test_result == ['True'], test_result


def check_firewall(
        agent_name, target_ip, target_port,
        win_py='C:/salt/bin/python.exe',
        win_tmp='C:/Windows/TEMP',
        linux_py='python',
        linux_tmp='/tmp',
        linux_nc=True
):
    try:
        agent_list = agent_name if isinstance(agent_name, list) else [agent_name]
        assert len(agent_list) == len(set(agent_list)), 'There is an invalid agent name'
        pc_list = list(set(SaltMinion.objects.filter(name__in=agent_list).values_list('env', 'os')))
        assert len(pc_list) == 1, 'The same batch of os and env must be the same'
        env, os = pc_list[0]
        salt = Salt(env)
        if os == 'Windows':
            return check_by_script(salt, agent_list, target_ip, target_port, win_py, win_tmp)
        else:
            if linux_nc:
                result, back = salt.shell(agent_list, f'[ -n "$(nc -z -w 1 {target_ip} {target_port}|grep succeeded)" ] && echo True || echo False')
                assert result, 'Can not be checked'
                test_result = list(set(back['return'][0].values()))
                return test_result == ['True'], test_result
            else:
                return check_by_script(salt, agent_list, target_ip, target_port, linux_py, linux_tmp)
    except AssertionError as e:
        return False, str(e)
    except Exception as e:
        return False, repr(e)
