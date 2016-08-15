# coding=utf-8
from django.http import HttpResponse
from django.shortcuts import render


# Create your views here.
def index(request):
    return render(request, 'om/index.html')


def default_content(_):
    return HttpResponse('开始页面内容')


def index_content(_):
    return HttpResponse('首页内容')


def quick_exec_script(request):
    return render(request, 'om/quick_exec_script.html')


def quick_upload_file(request):
    return render(request, 'om/quick_upload_file.html')


def exec_flow(request):
    return HttpResponse('执行作业流')


def new_flow(request):
    return render(request, 'om/new_flow.html')


def edit_job(request):
    return render(request, 'om/edit_job.html')


def action_history(request):
    return render(request, 'om/action_history.html')
