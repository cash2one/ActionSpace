# coding=utf-8
import sys
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import User, AnonymousUser
from django.views.debug import technical_500_response
from om.models import CallLog


# noinspection PyMethodMayBeStatic
class SupperDebug(MiddlewareMixin):
    # noinspection PyBroadException
    def process_request(self, request):
        try:
            full_path = request.get_full_path()
            if full_path != '/ok':
                user = User.objects.get_or_create(username='not_login_yet', is_active=False)[0] if isinstance(request.user, AnonymousUser) else request.user
                CallLog.objects.create(
                    user=user,
                    type='request',
                    action=full_path,
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
