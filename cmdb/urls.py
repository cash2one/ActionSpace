# coding=utf-8
from django.conf.urls import url
from cmdb import views


app_name = 'cmdb'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^get_action_list/$', views.get_action_list, name='get_action_list'),
]
