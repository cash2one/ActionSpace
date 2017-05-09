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
    url(r'^activity_status/$', views.activity_status, name='activity_status'),
    url(r'^activity_vote/$', views.activity_vote, name='activity_vote'),
    url(r'^make_firewall_table/$', views.make_firewall_table, name='make_firewall_table'),
    url(r'^common_address/$', views.common_address, name='common_address'),
    url(r'^get_sh_zs/$', views.get_sh_zs, name='get_sh_zs'),
    url(r'^check_firewall/$', views.check_firewall, name='check_firewall'),
]
