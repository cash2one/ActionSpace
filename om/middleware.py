# coding=utf-8
import sys
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import User
from django.views.debug import technical_500_response
from om.models import CallLog


# noinspection PyMethodMayBeStatic
class SupperDebug(MiddlewareMixin):
    # noinspection PyBroadException
    def process_request(self, request):
        try:
            CallLog.objects.create(
                user=User.objects.get(username=request.user.username),
                type='request',
                action=request.get_full_path(),
                detail=request.META
            )
        except Exception as e:
            print(e)
        return None

    def process_exception(self, request, exception):
        print(exception)
        print(request.META.get('REMOTE_ADDR'))
        if request.user.is_superuser:
            return technical_500_response(request, *sys.exc_info())
