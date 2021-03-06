# coding: utf-8
from switch.models import *
from celery import shared_task
from om.models import MacAddr
from io import StringIO
from collections import OrderedDict
import re
import subprocess
import os
import time


# noinspection PyCompatibility
class Scan(object):
    def __init__(self, clean_first=False):
        if clean_first:
            self.clean_data()
        self.search = Search.objects.create()

    @staticmethod
    def clean_data():
        Machine.objects.all().delete()
        BridgePort.objects.all().delete()
        NetworkInterface.objects.all().delete()
        PortChannel.objects.all().delete()
        StepResult.objects.all().delete()
        Search.objects.all().delete()
        Switch.objects.filter(is_group=False).delete()

    @staticmethod
    def call(cmd):
        if False:
            return os.popen(cmd).read()
        else:
            output = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out = ''
            # noinspection PyBroadException
            try:
                out = output.stdout.read().decode('unicode-escape')
                err = output.stderr.read().decode('unicode-escape')
                if err != '':
                    print('err:{err}'.format(err=err))
            except Exception as _:
                print(cmd, output.stdout.read(), output.stderr.read())
            return out

    def process(self, step, kargs, func, *args):
        template = CmdTemplate.objects.get(step=step)
        kargs['oid'] = template.oid
        cmd = template.template.format(**kargs)
        output = self.call(cmd)
        StepResult.objects.create(cmd_info=cmd, step=step, search=self.search, output=output)
        if isinstance(func, list):
            func_yes, func_no = func
        else:
            func_yes, func_no = func, None
        for line in StringIO(output).readlines():
            if line.strip('\t\r\n "') == '':
                continue
            result = re.search(template.reg, line)
            if result is None:
                if func_no is not None:
                    func_no(line, *args)
            else:
                func_yes(result, *args)

    def scan_switch(self, result, peer_switch, group_switch):
        """
            4 对端设备ip 地址
            5 对端设备描述
            6 对端设备名称
            7 对端设备接口名称
            8 对端设备型号
            9 对端设备类型（交换机，路由器或主机）
        """
        action_num = result.group('action_num')
        peer_switch[result.group('action_num')] = result.group('peer_info').strip('"')
        if action_num == '9':
            ip = peer_switch['4']
            switch_name = peer_switch['6']
            if ip != '':
                try:
                    ip = '.'.join([str(int(x, 16)) for x in ip.strip('"').split()])
                except Exception as e:
                    print(ip)
                    print(e)
                    return
                # uat_condition = ip in ['10.25.155.235', '10.25.154.242']
                uat_condition = True
                if not ip.startswith('172.') and not any([x for x in ['HB'] if x in switch_name]) and uat_condition:
                    switch, _ = Switch.objects.get_or_create(ip=ip)
                    switch.desc = peer_switch['5']
                    switch.name = switch_name
                    switch.model = peer_switch['8']
                    switch.s_type = peer_switch['9']
                    switch.add_uplink_switch(group_switch.ip)
                    switch.save()
                    net_port_name_before = peer_switch['7'].strip('"')
                    net_port_name_after = net_port_name_before.replace('GigabitEthernet', 'Gi').replace(
                        'FastEthernet', 'Fa')
                    if net_port_name_after == 'Gi1/48':
                        print(group_switch.ip, ip, net_port_name_before, net_port_name_after)
                    net_port, _ = NetworkInterface.objects.get_or_create(
                        name=net_port_name_after, switch=switch, search=self.search
                    )
                    net_port.connect_type = 'up'
                    net_port.save()
            else:
                print('can not get switch ip for [{switch}]'.format(switch=peer_switch))

    def scan_port(self, result, switch):
        if switch.is_group:
            return
        # # 不符合命名规范的网口跳过
        # if not re.search(r'\w+/?\d+/\d+|mgmt\d+|FastEthernet\d+|Fa\d+', result.group('name')):
        #     print(f'skip net_port {result.group("name")} in switch {switch.ip}')
        #     return#
        net_port, _ = NetworkInterface.objects.get_or_create(
            name=result.group('name'), switch=switch, search=self.search
        )
        net_port.num = str(result.group('port_num'))
        net_port.save()

    def scan_port_channel(self, result, switch):
        try:
            begin = time.time()
            po_if_index = int(result.group('po_if_index'))
            phy_if_index = int(result.group('phy_if_index'))
            po_c = NetworkInterface.objects.get(switch=switch, num=po_if_index, search=self.search)
            phy_c = NetworkInterface.objects.get(switch=switch, num=phy_if_index, search=self.search)
            poc, created = PortChannel.objects.get_or_create(
                switch=switch, port_channel=po_c, connect_type=phy_c.connect_type, search=self.search
            )
            if created:
                poc.save()
            poc.physical_channel.add(phy_c)
            poc.save()
            end = time.time()
            print(f'scan_port_channel(switch={switch.ip}):{end - begin}')
        except NetworkInterface.DoesNotExist as _:
            print(f'scan_port_channel fail:{switch.ip}, {po_if_index}, {phy_if_index}, ')

    def vlan_yes(self, result, switch, vlan_id):
        begin = time.time()
        machine, _ = Machine.objects.get_or_create(
            mac_hex=result.group('mac_hex'), mac_decimal=result.group('mac_decimal'),
            switch=switch, search=self.search
        )
        machine.vlan = vlan_id
        machine.save()
        end = time.time()
        print('vlan_yes(switch={switch},vlan={vlan}):{ct:.3f}'.format(switch=switch.ip, vlan=vlan_id, ct=end-begin))

    def vlan_no(self, result, switch, vlan_id):
        begin = time.time()
        machine_result = re.search(CmdTemplate.objects.get(step=41).reg, result)
        if machine_result is not None:
            mac_decimal = machine_result.group('mac_decimal')
            mac_hex_list = []
            for i in mac_decimal.split('.'):
                h = hex(int(i)).replace('0x', '').upper()
                if len(h) == 1:
                    h = '0{nh}'.format(nh=h)
                mac_hex_list.append(h)
            mac_hex = ' '.join(mac_hex_list)
            machine, _ = Machine.objects.get_or_create(
                mac_hex=mac_hex, mac_decimal=mac_decimal, switch=switch, search=self.search
            )
            machine.vlan = vlan_id
            machine.save()
            # print('try 41:[{dec}]->[{hex}] in {switch}@{vlan}'.format(dec=mac_decimal, hex=mac_hex, switch=switch.ip, vlan=vlan_id))
        else:
            print('can not analyze machine[{mac}] in {switch}@{vlan}'.format(
                mac=result, switch=switch.ip, vlan=vlan_id))
        end = time.time()
        print('vlan_yes(switch={switch},vlan={vlan}):{ct:.3f}'.format(switch=switch.ip, vlan=vlan_id, ct=end-begin))

    def scan_bridge(self, result, switch, vlan_id):
        begin = time.time()
        bridge, _ = BridgePort.objects.get_or_create(
            num=result.group('port_num'), switch=switch, vlan=vlan_id,
            mac_decimal=result.group('mac_decimal'), search=self.search
        )
        bridge.save()
        end = time.time()
        print('scan_bridge(switch={switch},vlan={vlan}):{ct:.3f}'.format(switch=switch.ip, vlan=vlan_id, ct=end-begin))

    def update_port(self, result, switch):
        begin = time.time()
        try:
            net_face = NetworkInterface.objects.get(
                switch=switch, num=result.group('net_port_num'), search=self.search
            )
            for bridge in BridgePort.objects.filter(
                    num=result.group('port_num'), switch=switch, search=self. search
            ):
                bridge.net_port = net_face
                bridge.save()
                machines = Machine.objects.filter(
                    mac_decimal=bridge.mac_decimal, switch=switch, search=self.search
                )
                if net_face.connect_type in ['up', 'down']:
                    machines.delete()
                else:
                    port_chan = PortChannel.objects.filter(switch=switch, port_channel=net_face)
                    if port_chan.exists() and port_chan.first().connect_type in ['up', 'down']:
                        machines.delete()
                    else:
                        machines.update(net_face=net_face)
        except NetworkInterface.DoesNotExist as _:
            pass
        except Machine.MultipleObjectsReturned as e:
            print(e)
        end = time.time()
        print('update_port(switch={switch}):{ct:.3f}'.format(switch=switch.ip, ct=end-begin))

    def process_vlan(self, result, switch):
        vlan_id = result.group('vlan_id')
        kargs = {'vlan_id': vlan_id, 'ip': switch.ip, 'communication': switch.communication}
        self.process(4, kargs, [self.vlan_yes, self.vlan_no], switch, vlan_id)
        self.process(5, kargs, self.scan_bridge, switch, vlan_id)
        self.process(6, kargs, self.update_port, switch)

    def scan_arp(self, result):
        ip = result.group('ip')
        mac_hex = result.group('mac_hex')
        try:
            m = Machine.objects.get(mac_hex=mac_hex, search=self.search)
            m.desc = ip
            m.save()
        except Machine.DoesNotExist as _:
            pass
        except Machine.MultipleObjectsReturned as e:
            print(e)
            print(Machine.objects.filter(mac_hex=mac_hex, search=self.search))

    def update_minion(self, all_minion=False):
        machines = Machine.objects.all()
        if not all_minion:
            machines.filter(search=self.search)
        for mc in machines:
            mc_hex = mc.mac_hex.strip().replace(' ', ':')
            for mac in MacAddr.objects.select_related('minion').filter(mac_hex__iexact=mc_hex):
                mc.minion = mac.minion
                mc.save()

    def run(self):
        run_begin = time.time()

        # 1 从汇聚交换机里遍历出所有的交换机信息
        for group_switch in Switch.objects.filter(is_group=True):
            kargs = {'ip': group_switch.ip, 'communication': group_switch.communication}
            peer_switch = OrderedDict()
            self.process(1, kargs, self.scan_switch, peer_switch, group_switch)

        # 2 遍历出所有交换机的网口
        for switch in Switch.objects.all():
            kargs = {'ip': switch.ip, 'communication': switch.communication}
            self.process(2, kargs, self.scan_port, switch)  # 扫描端口
            self.process(8, kargs, self.scan_port_channel, switch)  # 扫描捆绑口

        # 3 处理所有非汇聚交换机里的vlan信息
        for switch in Switch.objects.exclude(is_group=True):
            print('begin({ip})'.format(ip=switch.ip))
            kargs = {'ip': switch.ip, 'communication': switch.communication}
            self.process(3, kargs, self.process_vlan, switch)

        # 从om的salt信息里更新出salt-agent-name，包含了主机名和ip
        self.update_minion()

        # 7从汇聚交换机的arp表里更新扫描到的主机IP，作为上一步的补充
        for switch in Switch.objects.filter(is_group=True):
            kargs = {'ip': switch.ip, 'communication': switch.communication}
            self.process(7, kargs, self.scan_arp)
        run_end = time.time()
        print(f'run cost time:{run_end-run_begin:.3f}(s)')


@shared_task
def switch_test(who='wqz'):
    print(who)
