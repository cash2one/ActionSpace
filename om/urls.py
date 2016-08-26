# coding=utf-8
from django.conf.urls import url
from . import views

urlpatterns = [
    url(r"^$", views.index, name='index'),
    url(r'^default_content/$', views.default_content, name='default_content'),
    url(r'^index_content/$', views.index_content, name='index_content'),
    url(r'^quick_exec_script/$', views.quick_exec_script, name='quick_exec_script'),
    url(r'^quick_upload_file/$', views.quick_upload_file, name='quick_upload_file'),
    url(r'^exec_flow/$', views.exec_flow, name='exec_flow'),
    url(r'^new_flow/$', views.new_flow, name='new_flow'),
    url(r'^action_history/$', views.action_history, name='action_history'),
    url(r'^edit_job/$', views.edit_job, name='edit_job'),
     url(r'^edit_flow/$', views.edit_flow, name='edit_flow'),
    url(r'^choose_server/$', views.choose_server, name='choose_server'),
    url(r'^get_server_list/$', views.get_server_list, name='get_server_list'),
    url(r'^action_detail/$', views.action_detail, name='action_detail'),
    url(r'^get_action_history_list/$', views.get_action_history_list, name='get_action_history_list'),
    url(r'^choose_server_result/$', views.choose_server_result, name='choose_server_result'),
]
