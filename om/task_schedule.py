# coding=utf-8
import time
from django.utils import timezone
from random import randint
from om.models import Task, Flow, JobGroup, Job


def refresh_task():
    for task in Task.objects.all():
        task.task_status = 'no_run'
        task.save()


def get_un_run_task_list():
    return Task.objects.filter(task_status='no_run')


def exec_task(refresh=False):
    if refresh:
        refresh_task()
    for task in get_un_run_task_list():
        # flow =# task.exec_flow
        # group_list = flow.job_group_list.split(',')
        # group_list = JobGroup.objects.filter(id in group_list)
        # for group in Job
        task.start_time = timezone.now()
        time.sleep(randint(1, 5))
        task_status = [x[0] for x in Task.TASK_STATUS if x[0] != 'no_run']
        task.task_status = task_status[randint(0, len(task_status)-1)]
        task.save()
