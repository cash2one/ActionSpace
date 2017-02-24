# coding=utf-8
from django.http import HttpResponse
from django.contrib.auth.models import Group, User
from django.contrib import auth
from django.http import HttpResponseRedirect
from switch.models import Machine
from django.shortcuts import render
from django import forms

from ActionSpace.serializers import UserSerializer, GroupSerializer, ServerSerializer, MachineSerializer
from rest_framework import viewsets
from om.models import Computer

# from django.shortcuts import render
# ViewSets define the view behavior.

# 权限列表（permission_classes里）：
# AllowAny
# IsAuthenticated
# IsAdminUser
# IsAuthenticatedOrReadOnly
# DjangoModelPermissions
# DjangoModelPermissionsOrAnonReadOnly
# DjangoObjectPermissions


class UserForm(forms.Form):
    username = forms.CharField(label='用户名', max_length=100)
    password = forms.CharField(label='密码', widget=forms.PasswordInput())


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class ServerViewSet(viewsets.ReadOnlyModelViewSet):
    # renderer_classes = (JSONRenderer,)
    queryset = Computer.objects.all()
    serializer_class = ServerSerializer


class MachineViewSet(viewsets.ReadOnlyModelViewSet):
    # renderer_classes = (JSONRenderer,)
    queryset = Machine.objects.all()
    serializer_class = MachineSerializer


# Create your views here.
def index(_):
    return HttpResponse("<script language='javascript'>document.location = 'om/'</script>")


def ok(_):
    return HttpResponse('OK')


def login(request):
    if request.method == 'POST':
        uf = UserForm(request.POST)
        if uf.is_valid():
            username = uf.cleaned_data['username']
            password = uf.cleaned_data['password']
            user = auth.authenticate(username=username.lower(), password=password)
            if user:
                # noinspection PyBroadException
                try:
                    if not user.is_active:
                        return render(request, 'om/login.html', {'errmsg': '用户已被锁定，请联系管理员！'})
                    auth.login(request, user)
                    return HttpResponseRedirect(request.GET['next'])
                except BaseException as _:
                    return render(request, 'om/login.html', {'errmsg': '登录失败！'})
            else:
                return render(request, 'om/login.html', {'errmsg': '请输入正确的账号和密码！'})
    else:
        msg = {}
        #  user = getattr(request, 'user', None)
        #  if user and not user.is_active:
        #      msg['errmsg'] = '用户已被锁定，请联系管理员！'
        return render(request, 'om/login.html', msg)


def guest_login(request):
    import traceback
    # noinspection PyBroadException
    try:
        user = auth.authenticate(username='guest', password='guest_guest')
        if not user or not user.is_active:
            return HttpResponseRedirect('/om/')
        auth.login(request, user)
    except BaseException as _:
        print(traceback.format_exc())
    return HttpResponseRedirect('/om/')
