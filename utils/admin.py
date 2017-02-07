from django.contrib import admin
from utils.models import *


# Register your models here.
@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'voted', 'join', 'guess')
    list_display_links = ('id', 'user', 'guess')
    search_fields = ('id', 'user__username', 'guess')
    actions = ['mark_voted', 'mark_not_voted', 'mark_join', 'mark_not_join']

    def mark_voted(self, _, queryset):
        queryset.update(voted=True)
    mark_voted.short_description = '设置为已投票'

    def mark_not_voted(self, _, queryset):
        queryset.update(voted=False)
    mark_not_voted.short_description = '设置为未投票'

    def mark_join(self, _, queryset):
        queryset.update(join=True)
    mark_join.short_description = '设置为参赛'

    def mark_not_join(self, _, queryset):
        queryset.update(join=False)
    mark_not_join.short_description = '设置为不参赛'
