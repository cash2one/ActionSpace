# coding=utf-8
from django.http import HttpResponse
from django.contrib.auth.models import User, Group
from rest_framework import permissions
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from ActionSpace.serializers import UserSerializer, GroupSerializer, ServerSerializer
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
    queryset = Computer.objects.all()
    serializer_class = ServerSerializer


# Create your views here.
def index(_):
    return HttpResponse("<script language='javascript'>document.location = 'om/'</script>")
