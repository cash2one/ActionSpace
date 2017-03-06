from django.db import models
from om.models import SaltMinion, Computer


# Create your models here.
class Search(models.Model):
    exec_user = models.CharField(max_length=100, verbose_name='执行者', default='')
    search_time = models.DateTimeField(verbose_name='查询时间', auto_now_add=True)

    def __str__(self):
        return repr(self.pk)

    class Meta:
        verbose_name = '查询信息'
        verbose_name_plural = '查询信息'


class CmdTemplate(models.Model):
    step = models.IntegerField(verbose_name='命令编号')
    template = models.CharField(max_length=200, verbose_name='命令模板', default='')
    oid = models.CharField(max_length=100, verbose_name='OID', default='')
    reg = models.CharField(max_length=400, verbose_name='解析表达式')
    desc = models.TextField(verbose_name='步骤说明', default='')

    def __str__(self):
        return repr(self.step)

    class Meta:
        verbose_name = '命令模板'
        verbose_name_plural = '命令模板'


class StepResult(models.Model):
    output = models.TextField(verbose_name='输出', default='')
    cmd_info = models.CharField(max_length=200, verbose_name='命令', default='')
    step = models.IntegerField(verbose_name='执行步骤', default=0)
    search = models.ForeignKey(Search, verbose_name='查询批次', null=True)

    def __str__(self):
        return repr(self.pk)

    class Meta:
        verbose_name = '查询结果'
        verbose_name_plural = '查询结果'


class Switch(models.Model):
    ip = models.GenericIPAddressField(verbose_name='IP地址')
    area = models.CharField(max_length=20, verbose_name='网络区', default='')
    communication = models.CharField(max_length=100, verbose_name='通讯密码', default='app2gdemo')
    name = models.CharField(max_length=100, verbose_name='设备名称', default='')
    model = models.CharField(max_length=100, verbose_name='设备型号', default='')
    TYPE_CHOICES = (('28', '交换机'), ('29', '路由器'), ('-1', '未知'))
    s_type = models.CharField(max_length=100, choices=TYPE_CHOICES, verbose_name='设备类型', default='-1')
    is_group = models.BooleanField(default=False, verbose_name='是否为汇聚交换机')
    uplink_switch = models.CharField(max_length=200, verbose_name='上联交换机', default='')
    desc = models.TextField(verbose_name='设备描述', default='')

    def __str__(self):
        return self.ip

    def add_uplink_switch(self, ip):
        new_set = set(self.uplink_switch.split(','))
        new_set.add(ip)
        self.uplink_switch = ','.join(new_set)
        self.uplink_switch = self.uplink_switch.strip(',')

    class Meta:
        verbose_name = '交换机'
        verbose_name_plural = '交换机'


class NetworkInterface(models.Model):
    name = models.CharField(max_length=100, verbose_name='网口名', default='')
    switch = models.ForeignKey(Switch, verbose_name='交换机')
    num = models.IntegerField(verbose_name='网口号', default=-1)
    CONNECT_TYPE = (('down', '下联交换机'), ('up', '上联交换机'), ('host', '连接主机'), ('other', '其他'))
    connect_type = models.CharField(max_length=10, choices=CONNECT_TYPE, verbose_name='接口类型', default='other')
    search = models.ForeignKey(Search, verbose_name='查询批次', null=True)

    def __str__(self):
        return self.name

    def switch_ip(self):
        return self.switch.ip
    switch_ip.short_description = '交换机IP'

    class Meta:
        verbose_name = '网口'
        verbose_name_plural = '网口'
        unique_together = ('name', 'switch', 'search')


class BridgePort(models.Model):
    num = models.IntegerField(verbose_name='桥接口')
    switch = models.ForeignKey(Switch, verbose_name='交换机', null=True)
    vlan = models.IntegerField(verbose_name='VLAN编号', null=True)  # 154
    mac_decimal = models.CharField(max_length=100, verbose_name='MAC地址（十进制）', default='')
    net_port = models.ForeignKey(NetworkInterface, verbose_name='网口', null=True)
    search = models.ForeignKey(Search, verbose_name='查询批次', null=True)

    def net_port_name(self):
        return 'NA' if self.net_port is None else self.net_port.name

    class Meta:
        verbose_name = '桥接口'
        verbose_name_plural = '桥接口'
        unique_together = ('num', 'switch', 'vlan', 'mac_decimal', 'search')


class Machine(models.Model):
    mac_hex = models.CharField(max_length=100, verbose_name='MAC地址（十六进制）')
    mac_decimal = models.CharField(max_length=100, verbose_name='MAC地址（十进制）')
    switch = models.ForeignKey(Switch, verbose_name='交换机', null=True)
    vlan = models.IntegerField(verbose_name='VLAN编号', null=True)
    net_face = models.ForeignKey(NetworkInterface, verbose_name='网口', null=True)
    minion = models.ForeignKey(SaltMinion, verbose_name='主机', null=True)
    search = models.ForeignKey(Search, verbose_name='查询批次', null=True)
    desc = models.CharField(max_length=200, verbose_name='备注', default='')

    def __str__(self):
        return repr(self.mac_hex)

    def entity_name(self):
        try:
            if self.minion is not None:
                return Computer.objects.prefetch_related('entity').get(agent_name__iexact=self.minion.name).entity_name()
            return 'NA'
        except Computer.DoesNotExist as _:
            return 'NA'
    entity_name.short_description = '逻辑实体'

    class Meta:
        verbose_name = '主机'
        verbose_name_plural = '主机'
