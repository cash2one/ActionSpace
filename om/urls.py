# coding=utf-8
from django.conf.urls import url
from . import views

app_name = 'om'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^default_content/$', views.default_content, name='default_content'),
    url(r'^index_content/$', views.index_content, name='index_content'),
    url(r'^quick_exec_script/$', views.quick_exec_script, name='quick_exec_script'),
    url(r'^quick_upload_file/$', views.quick_upload_file, name='quick_upload_file'),
    url(r'^exec_flow/$', views.exec_flow, name='exec_flow'),
    url(r'^new_flow/$', views.new_flow, name='new_flow'),
    url(r'^action_history/$', views.action_history, name='action_history'),
    url(r'^edit_job/(?P<job_id>[0-9]+)/$', views.edit_job, name='edit_job'),
    url(r'^edit_flow/(?P<flow_id>[0-9]+)/$', views.edit_flow, name='edit_flow'),
    url(r'^choose_server/$', views.choose_server, name='choose_server'),
    url(r'^get_server_list/$', views.get_server_list, name='get_server_list'),
    url(r'^action_detail/$', views.action_detail, name='action_detail'),
    url(r'^get_action_history_list/$', views.get_action_history_list, name='get_action_history_list'),
    url(r'^choose_server_result/$', views.choose_server_result, name='choose_server_result'),
    url(r'^save_edit_flow/$', views.save_edit_flow, name='save_edit_flow'),
    url(r'^new_job/(?P<job_group_id>[0-9]+)/$', views.new_job, name='new_job_for_group'),
    url(r'^new_group/(?P<flow_id>[0-9]+)/$', views.new_group, name='new_group'),
    url(r'^del_job_in_group/(?P<group_id>[0-9]+)/(?P<job_id>[0-9]+)/$', views.del_job_in_group, name='del_job_in_group'),
    url(r'^del_group_inf_flow/(?P<flow_id>[0-9]+)/(?P<group_id>[0-9]+)/$', views.del_group_in_flow, name='del_group_in_flow'),
    url(r'^edit_group/(?P<group_id>[0-9]+)/$', views.edit_group, name='edit_group'),
]
