from django.contrib import admin
from switch.models import *


# Register your models here.
@admin.register(Switch)
class SwitchAdmin(admin.ModelAdmin):
    list_display = ('ip', 'area', 'name', 'uplink_switch', 'model', 'is_group')
    search_fields = ('ip', 'area', 'name', 'uplink_switch', 'model', 'desc')
    list_filter = ('model', 'is_group')


@admin.register(NetworkInterface)
class NetworkInterfaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'num', 'switch_ip', 'connect_type')
    search_fields = ('name', 'num', 'switch__ip')
    list_filter = ('switch__ip', )


@admin.register(BridgePort)
class BridgePortAdmin(admin.ModelAdmin):
    list_display = ('num', 'switch', 'net_port_name')
    search_fields = ('num',)


class MachineFilter(admin.SimpleListFilter):
    title = '机器过滤'
    parameter_name = 'machine_state'

    def lookups(self, request, model_admin):
        base_search = (
            (0, '能找到IP'),
            (1, '找不到IP'),
            (2, '能找到网口'),
            (3, '找不到网口'),
        )
        for s in Switch.objects.all():
            base_search += ((len(base_search), '交换机ip：{ip}'.format(ip=s.ip)),)
        for v in Search.objects.all():
            base_search += ((len(base_search), '查询批次：{num}'.format(num=v.id)),)
        return base_search

    def queryset(self, request, queryset):
        if self.value():
            name = [x[1] for x in self.lookup_choices if x[0] == int(self.value())][0]
            if int(self.value()) == 0:
                return queryset.exclude(minion__isnull=True)
            elif int(self.value()) == 1:
                return queryset.filter(minion__isnull=True)
            if int(self.value()) == 2:
                return queryset.exclude(net_face__isnull=True)
            elif int(self.value()) == 3:
                return queryset.filter(net_face__isnull=True)
            else:
                if name.startswith('交换机ip'):
                    return queryset.filter(switch__ip=name.replace('交换机ip：', ''))
                elif name.startswith('查询批次'):
                    return queryset.filter(search__id=name.replace('查询批次：', ''))
                else:
                    return queryset


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ('minion', 'entity_name', 'switch', 'net_face', 'vlan', 'mac_hex', 'mac_decimal', 'search')
    list_display_links = ('mac_hex', 'mac_decimal')
    search_fields = ('id', 'mac_hex', 'mac_decimal', 'switch__ip')
    list_filter = (MachineFilter,)


@admin.register(StepResult)
class StepResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'cmd_info', 'step', 'search')
    readonly_fields = ('output', 'cmd_info', 'step', 'search')
    search_fields = ('cmd_info', 'step')


@admin.register(CmdTemplate)
class CmdTemplateAdmin(admin.ModelAdmin):
    list_display = ('step', 'template', 'desc', 'oid', 'reg')
    search_fields = ('step', 'template', 'oid', 'reg', 'desc')
    ordering = ['step']


@admin.register(Search)
class SearchAdmin(admin.ModelAdmin):
    list_display = ('id', 'exec_user', 'search_time')
    search_fields = ('id', 'exec_user', 'search_time')
