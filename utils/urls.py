# coding=utf-8
from django.conf.urls import url
from utils import views

app_name = 'utils'
urlpatterns = [
    url(r'^picutil/$', views.picutil, name='picutil'),
    url(r'^query_net_area/$', views.query_net_area, name='query_net_area'),
    url(r'^net/$', views.net, name='net'),
    url(r'^activity/$', views.activity, name='activity'),
    url(r'^activity_data/$', views.activity_data, name='activity_data'),
    url(r'^activity_vote/$', views.activity_vote, name='activity_vote'),
    url(r'^make_firewall_table/$', views.make_firewall_table, name='make_firewall_table'),
]
