# coding=utf-8
from django.http import HttpResponse
from django.contrib.auth.models import User, Group
from rest_framework import permissions
from serializers import UserSerializer, GroupSerializer
from rest_framework import viewsets
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


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAdminUser,)


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = (permissions.DjangoModelPermissions,)


# Create your views here.
def index(_):
    return HttpResponse("<script language='javascript'>document.location = 'om/'</script>")
