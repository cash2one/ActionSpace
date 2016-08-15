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
]
