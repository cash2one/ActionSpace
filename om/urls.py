# coding=utf-8
from django.conf.urls import url, include
from om import views

app_name = 'om'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^default_content/$', views.default_content, name='default_content'),
    url(r'^no_permission/$', views.no_permission, name='no_permission'),
    url(r'^quick_exec_script/$', views.quick_exec_script, name='quick_exec_script'),
    url(r'^quick_upload_file/$', views.quick_upload_file, name='quick_upload_file'),
    url(r'^exec_flow/$', views.exec_flow, name='exec_flow'),
    url(r'^get_flow_list/$', views.get_flow_list, name='get_flow_list'),
    url(r'^new_flow/$', views.new_flow, name='new_flow'),
    url(r'^action_history/$', views.action_history, name='action_history'),
    url(r'^edit_job/(?P<job_id>[0-9]+)/$', views.edit_job, name='edit_job'),
    url(r'^edit_flow/(?P<flow_id>[0-9]+)/$', views.edit_flow, name='edit_flow'),
    url(r'^choose_server/$', views.choose_server, name='choose_server'),
    url(r'^get_server_list/$', views.get_server_list, name='get_server_list'),
    url(r'^get_task_server_list/$', views.get_task_server_list, name='get_task_server_list'),
    url(r'^action_detail/(?P<task_id>[0-9]+)/$', views.action_detail, name='action_detail'),
    url(r'^flow_clone/(?P<flow_id>[0-9]+)/$', views.flow_clone, name='flow_clone'),
    url(r'^flow_delete/(?P<flow_id>[0-9]+)/(?P<username>[a-zA-Z0-9]+)/$', views.flow_delete, name='flow_delete'),
    url(r'^get_action_history_list/$', views.get_action_history_list, name='get_action_history_list'),
    url(r'^choose_server_result/$', views.choose_server_result, name='choose_server_result'),
    url(r'^save_edit_flow/$', views.save_edit_flow, name='save_edit_flow'),
    url(r'^new_job/(?P<job_group_id>[0-9]+)/$', views.new_job, name='new_job'),
    url(r'^new_group/(?P<flow_id>[0-9]+)/$', views.new_group, name='new_group'),
    url(r'^del_job_in_group/(?P<group_id>[0-9]+)/(?P<job_id>[0-9]+)/$', views.del_job_in_group, name='del_job_in_group'),
    url(r'^del_group_inf_flow/(?P<flow_id>[0-9]+)/(?P<group_id>[0-9]+)/$', views.del_group_in_flow, name='del_group_in_flow'),
    url(r'^edit_group/(?P<group_id>[0-9]+)/$', views.edit_group, name='edit_group'),
    url(r'^get_task_status/(?P<task_id>[0-9]+)/$', views.get_task_status, name='get_task_status'),
    url(r'^task_status/(?P<task_id>[0-9]+)/$', views.task_status, name='task_status'),
    url(r'^detail_content/(?P<task_id>[0-9]+)/$', views.detail_content, name='detail_content'),
    url(r'^confirm_task/(?P<task_id>[0-9]+)/(?P<flow_id>[0-9]+)/(?P<group_id>[0-9]+)/(?P<job_id>[0-9]+)/$', views.confirm_task, name='confirm_task'),
    url(r'^create_task/(?P<flow_id>[\-0-9]+)/(?P<job_id>[\-0-9]+)/$', views.create_task, name='create_task'),
    url(r'^redo_create_task/(?P<task_id>[0-9]+)/$', views.redo_create_task, name='redo_create_task'),
    url(r'^exec_task/(?P<task_id>[0-9]+)/$', views.exec_task, name='exec_task'),
    url(r'^approval_task/(?P<task_id>[0-9]+)/$', views.approval_task, name='approval_task'),
    url(r'^task_item_detail/(?P<task_job_id>[0-9]+)/$', views.task_item_detail, name='task_item_detail'),
    url(r'^get_common_script_content/(?P<s_id>[0-9]+)/$', views.get_common_script_content, name='get_common_script_content'),
    url(r'^set_group_host/(?P<group_id>[0-9]+)/$', views.set_group_host, name='set_group_host'),
    url(r'^chg_pwd/$', views.chg_pwd, name='chg_pwd'),
    url(r'^get_ip_host_list/$', views.get_ip_host_list, name='get_ip_host_list'),
    url(r'^unlock_win/$', views.unlock_win, name='unlock_win'),
    url(r'^show_server/$', views.show_server, name='show_server'),
    url(r'^update_flow_name/(?P<username>[a-zA-Z0-9]+)/(?P<flow_id>[0-9]+)/(?P<new_name>.+)/$', views.update_flow_name, name='update_flow_name'),
    url(r'^select_server_list/(?P<job_id>[\-0-9]+)/$', views.select_server_list, name='select_server_list'),
    url(r'^salt_status/$', views.salt_status, name='salt_status'),
    url(r'^salt_status_api/$', views.salt_status_api, name='salt_status_api'),
    url(r'^auto_task/$', views.auto_task, name='auto_task'),
    url(r'^modify_auto_task/(?P<task_id>[0-9]+)/$', views.modify_auto_task, name='modify_auto_task'),
    url(r'^delete_auto_task/(?P<task_id>[0-9]+)/$', views.delete_auto_task, name='delete_auto_task'),
    url(r'^auto_task_list/$', views.auto_task_list, name='auto_task_list'),
    url(r'^add_auto_task/$', views.add_auto_task, name='add_auto_task'),
    url(r'^job_quick_task/(?P<task_id>[0-9]+)/$', views.job_quick_task, name='job_quick_task'),
    url(r'^upload_file/$', views.upload_file, name='upload_file'),
    url(r'^get_server_file_list', views.get_server_file_list, name='get_server_file_list'),
    url(r'^get_grains', views.get_grains, name='get_grains'),
    url(r'^admin_action/(?P<name>.+)/$', views.admin_action, name='admin_action'),
    url(r'^set_flow_recipient/(?P<flow_id>[0-9]+)/(?P<mail_group_id>[\-0-9]+)/$', views.set_flow_recipient, name='set_flow_recipient'),
    url(r'^computer_task_json$', views.ComputerTaskView.as_view(), name='ComputerTaskView')
]
