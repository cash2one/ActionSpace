# coding=utf-8
from django.conf.urls import url
from switch import views

app_name = 'switch'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^get_machine_list/(?P<search_id>[0-9]+)/$', views.get_machine_list, name='get_machine_list'),
    url(r'^export_excel/(?P<search_id>[0-9]+)/$', views.export_excel, name='export_excel')
]
