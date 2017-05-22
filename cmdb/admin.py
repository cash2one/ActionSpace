from django.contrib import admin
from guardian.admin import GuardedModelAdmin
from cmdb.models import Action


# Register your models here.
@admin.register(Action)
class ActionAdmin(GuardedModelAdmin):
    list_display = ('id', 'name', 'status')
