from django.contrib import admin
from utils.models import *
from guardian.admin import GuardedModelAdmin


@admin.register(Activity)
class ActivityAdmin(GuardedModelAdmin):
    list_display = ('id', 'user', 'voted', 'join', 'guess', 'last_update')
    list_display_links = ('id', 'user', 'guess')
    search_fields = ('id', 'user__username', 'guess')
    actions = ['mark_voted', 'mark_not_voted', 'mark_join', 'mark_not_join']
    list_filter = ('voted', 'join')

    def mark_voted(self, _, queryset):
        queryset.update(voted=True, last_update=timezone.now())
    mark_voted.short_description = '设置为已投票'

    def mark_not_voted(self, _, queryset):
        queryset.update(voted=False, last_update=timezone.now())
    mark_not_voted.short_description = '设置为未投票'

    def mark_join(self, _, queryset):
        queryset.update(join=True, last_update=timezone.now())
    mark_join.short_description = '设置为参赛'

    def mark_not_join(self, _, queryset):
        queryset.update(join=False, last_update=timezone.now())
    mark_not_join.short_description = '设置为不参赛'


@admin.register(CommonAddress)
class CommonAddressAdmin(GuardedModelAdmin):
    list_display = ('id', 'name', 'url')
    search_fields = ('id', 'name', 'url')


class NetRegionInline(admin.TabularInline):
    model = NetRegion
    extra = 0
    show_change_link = True
    verbose_name = '网段'
    verbose_name_plural = '网段'


@admin.register(NetArea)
class NetAreaAdmin(GuardedModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('id', 'name')
    inlines = [NetRegionInline]


class NetInfoInline(admin.TabularInline):
    model = NetInfo
    extra = 0
    show_change_link = True
    verbose_name = 'IP段'
    verbose_name_plural = 'IP段'


@admin.register(NetRegion)
class NetRegionAdmin(GuardedModelAdmin):
    list_display = ('id', 'name', 'area')
    search_fields = ('id', 'name', 'area__name')
    list_filter = ('area',)
    inlines = [NetInfoInline]


@admin.register(NetInfo)
class NetInfoAdmin(GuardedModelAdmin):
    list_display = ('id', 'ip', 'mask', 'region')
    search_fields = ('id', 'ip', 'mask', 'region__area__name', 'region__name')
    list_filter = ('region__area', 'region')
