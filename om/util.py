# coding=utf-8
from __future__ import print_function
from __future__ import absolute_import
from random import randint
from celery import shared_task
from celery.utils.log import get_task_logger
from celery.result import AsyncResult
from django.utils import timezone

import pika
import time

MQ_URL = 'amqp://action_space:action_space@localhost:5672/%2F'
task_logger = get_task_logger(__name__)


# noinspection PyUnusedLocal
class TaskChange(object):
    def __init__(self, tid):
        self.task_id = str(tid)
        self.exchange_name = 'task_change'
        self.exchange_type = 'fanout'
        self.conn = pika.BlockingConnection(pika.URLParameters(MQ_URL))
        self.chan = self.conn.channel()

    def __task_change_callback(self, ch, method, properties, body):
        if body.decode() == self.task_id:
            self.chan.stop_consuming()

    def __close(self):
        self.chan.close()
        self.conn.close()

    def wait_change(self):
        queue_name = self.chan.queue_declare(exclusive=True, auto_delete=True).method.queue
        self.chan.exchange_declare(exchange=self.exchange_name, type=self.exchange_type, auto_delete=True)
        self.chan.queue_bind(exchange=self.exchange_name, queue=queue_name)
        self.chan.basic_consume(consumer_callback=self.__task_change_callback, queue=queue_name, no_ack=True)
        self.chan.start_consuming()
        self.__close()

    def send_change(self):
        self.chan.exchange_declare(exchange=self.exchange_name, type=self.exchange_type, auto_delete=True)
        self.chan.basic_publish(exchange=self.exchange_name, routing_key='', body=self.task_id)
        self.__close()


# noinspection PyUnusedLocal
class TaskConfirm(object):
    def __init__(self, key):
        self.confirm_key = key
        self.exchange_name = 'task_confirm'
        self.exchange_type = 'fanout'
        self.conn = pika.BlockingConnection(pika.URLParameters(MQ_URL))
        self.chan = self.conn.channel()

    def __task_confirm_callback(self, ch, method, properties, body):
        if body.decode() == self.confirm_key:
            self.chan.stop_consuming()

    def __close(self):
        self.chan.close()
        self.conn.close()

    def wait_confirm(self):
        queue_name = self.chan.queue_declare(exclusive=True, auto_delete=True).method.queue
        self.chan.exchange_declare(exchange=self.exchange_name, type=self.exchange_type, auto_delete=True)
        self.chan.queue_bind(exchange=self.exchange_name, queue=queue_name)
        self.chan.basic_consume(consumer_callback=self.__task_confirm_callback, queue=queue_name, no_ack=True)
        self.chan.start_consuming()
        self.__close()

    def send_confirm(self):
        self.chan.exchange_declare(exchange=self.exchange_name, type=self.exchange_type, auto_delete=True)
        self.chan.basic_publish(exchange=self.exchange_name, routing_key='', body=self.confirm_key)
        self.__close()


def str2arr(val, sep=',', digit_check=True):
    arr = []
    if val:
        arr = [x for x in val.split(sep) if not digit_check or x.isdigit()]
    return arr


def get_task_result(result_id):
    return AsyncResult(result_id)


def get_name(content):
    if isinstance(content, bytes):
        return content.decode()
    else:
        return content


@shared_task
def celery_exec_task(tid, sender):
    from om.models import Task
    task_logger.info('user=[%s], task_id=[%d]' % (sender, tid))
    task = Task.objects.get(pk=tid)
    t_flow = task.taskflow_set.first()
    task.run()

    for t_group in task.taskflow_set.first().taskjobgroup_set.all():
        for t_job in t_group.taskjob_set.all():
            t_job.begin_time = timezone.now()
            t_job.status = 'running'
            t_job.save()
            TaskChange(task.id).send_change()
            time.sleep(randint(1, 3))
            t_job.end_time = timezone.now()
            t_job.status = 'finish'
            t_job.exec_output = '已经在[{ip_list}]生执行成功！'.format(ip_list=t_job.server_list)
            if t_job.pause_when_finish:
                t_job.pause_need_confirm = True
                t_job.save()
                TaskChange(task.id).send_change()
                TaskConfirm('%s-%s-%s-%s' % (
                    str(task.id), str(t_flow.flow_id), t_group.group_id, t_job.job_id)).wait_confirm()
                t_job.pause_need_confirm = False
                t_job.save()
            else:
                t_job.save()
                TaskChange(task.id).send_change()
    task.finish()
    task.save()
    TaskChange(task.id).send_change()
    time.sleep(randint(1, 5))
    return u'执行完成'
