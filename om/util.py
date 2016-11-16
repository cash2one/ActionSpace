# coding=utf-8
from __future__ import absolute_import
from random import randint
from celery import shared_task
from celery.utils.log import get_task_logger
from celery.result import AsyncResult
from django.utils import timezone
from ActionSpace import settings
from om.proxy import Salt
from pprint import pformat
import json
import pika
import time
import os
import traceback

task_logger = get_task_logger(__name__)


# noinspection PyUnusedLocal
class TaskChange(object):
    def __init__(self, tid):
        self.task_id = str(tid)
        self.exchange_name = 'task_change'
        self.exchange_type = 'fanout'
        self.conn = pika.BlockingConnection(pika.URLParameters(settings.MQ_URL))
        self.chan = self.conn.channel()
        settings.logger.info('TaskChange: __init__ %s' % tid)

    def __task_change_callback(self, ch, method, properties, body):
        settings.logger.info('TaskChange: __task_change_callback %s' % body)
        if body.decode() == self.task_id:
            self.chan.stop_consuming()

    def __close(self):
        settings.logger.info('TaskChange: __close')
        self.chan.close()
        self.conn.close()

    def wait_change(self):
        settings.logger.info('TaskChange: wait_change')
        queue_name = self.chan.queue_declare(exclusive=True, auto_delete=True).method.queue
        self.chan.exchange_declare(exchange=self.exchange_name, type=self.exchange_type, auto_delete=True)
        self.chan.queue_bind(exchange=self.exchange_name, queue=queue_name)
        self.chan.basic_consume(consumer_callback=self.__task_change_callback, queue=queue_name, no_ack=True)
        self.chan.start_consuming()
        self.__close()

    def send_change(self):
        settings.logger.info('TaskChange: send_change')
        self.chan.exchange_declare(exchange=self.exchange_name, type=self.exchange_type, auto_delete=True)
        self.chan.basic_publish(exchange=self.exchange_name, routing_key='', body=self.task_id)
        self.__close()


# noinspection PyUnusedLocal
class TaskConfirm(object):
    def __init__(self, key):
        self.confirm_key = key
        self.exchange_name = 'task_confirm'
        self.exchange_type = 'fanout'
        self.conn = pika.BlockingConnection(pika.URLParameters(settings.MQ_URL))
        self.chan = self.conn.channel()
        settings.logger.info('TaskConfirm: __init__ %s' % key)

    def __task_confirm_callback(self, ch, method, properties, body):
        settings.logger.info('TaskConfirm: __task_confirm_callback %s' % body)
        if body.decode() == self.confirm_key:
            self.chan.stop_consuming()

    def __close(self):
        settings.logger.info('TaskConfirm: __close')
        self.chan.close()
        self.conn.close()

    def wait_confirm(self):
        settings.logger.info('TaskConfirm: wait_confirm')
        queue_name = self.chan.queue_declare(exclusive=True, auto_delete=True).method.queue
        self.chan.exchange_declare(exchange=self.exchange_name, type=self.exchange_type, auto_delete=True)
        self.chan.queue_bind(exchange=self.exchange_name, queue=queue_name)
        self.chan.basic_consume(consumer_callback=self.__task_confirm_callback, queue=queue_name, no_ack=True)
        self.chan.start_consuming()
        self.__close()

    def send_confirm(self):
        settings.logger.info('TaskConfirm: send_confirm')
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


def fmt_salt_out(val, use_json=False):
    if isinstance(val, dict):
        content = val.get('return', val)
    else:
        content = val
    if use_json:
        result = json.dumps(content, ensure_ascii=False, indent=4)
    else:
        result = pformat(content, width=400)
    replace_list = [(r'\r\n', ''), (r'\t', ''), (r'\n', (' '*3)), (r'\x1b[7l', '')]
    for ora, new in replace_list:
        result = result.replace(ora, new)
    return result


# noinspection PyUnresolvedReferences
@shared_task
def celery_exec_task(tid, sender):
    from om.models import Task, Computer, ServerFile
    task_logger.info('user=[%s], task_id=[%d]' % (sender, tid))
    settings.logger.info('celery_exec_task: user=[%s], task_id=[%d]' % (sender, tid))
    task = Task.objects.get(pk=tid)
    task.exec_user = sender
    t_flow = task.taskflow_set.first()
    task.run()

    for t_group in t_flow.taskjobgroup_set.all():
        for t_job in t_group.taskjob_set.all():
            t_job.begin_time = timezone.now()
            t_job.status = 'running'
            t_job.save()
            TaskChange(task.id).send_change()
            job_info = 'task_id[(tid)]:flow[{f_name}, {f_id}], group[{g_name}, {g_id}], job[j_name, j_id]'.format(
                tid=task.id, f_name=t_flow.name, f_id=t_flow.flow_id, g_name=t_group.name, g_id=t_group.group_id,
                j_name=t_job.name, j_id=t_job.job_id
            )

            # 脚本开始执行
            settings.logger.info('{job} begin run'.format(job=job_info))
            ips = str2arr(t_job.server_list, digit_check=False)

            if len(ips) > 0:
                env_type = Computer.objects.get(ip=ips[0]).env
                agents = [Computer.objects.get(ip=x).agent_name for x in ips]
                is_windows = Computer.objects.get(ip=ips[0]).sys == 'windows'
                cmd = ' '.join([t_job.script_content, t_job.script_param])
                try:
                    if t_job.job_type == 'SCRIPT':
                        if t_job.script_type == 'PY':
                            salt_result, salt_output = Salt(env_type).python(agents, cmd)
                        else:
                            exec_user = None if is_windows else t_job.exec_user
                            salt_result, salt_output = Salt(env_type).shell(agents, cmd, exec_user)
                        t_job.status = 'finish' if salt_result else 'run_fail'
                        t_job.exec_output = fmt_salt_out(salt_output)  # [1:-1].replace("\\n", "")
                    else:
                        file_list = [ServerFile.objects.get(pk=x).name for x in str2arr(t_job.file_name)]
                        if len(file_list) == 0:
                            t_job.status = 'run_fail'
                            t_job.exec_output = '没有指定要传输的文件'
                        else:
                            result_list = []
                            output_list = []
                            for file_to_trans in file_list:
                                if t_job.target_name.endswith('\\') or t_job.target_name.endswith('/'):
                                    target_path = os.path.join(t_job.target_name, file_to_trans)
                                else:
                                    target_path = t_job.target_name
                                salt_result, salt_output = Salt(env_type).file_trans(agents, file_to_trans, target_path)
                                result_list.append(salt_result)
                                output_list.append(salt_output)
                                if not salt_result:
                                    settings.logger.error()
                            t_job.status = 'finish' if all(result_list) else 'run_fail'
                            t_job.exec_output = fmt_salt_out(output_list)
                except Exception as e:
                    t_job.status = 'run_fail'
                    settings.logger.error(str(e))
                    settings.logger.error(traceback.format_exc())
                    t_job.exec_output = '执行出错，请检查作业配置是否有误！'
            else:
                t_job.status = 'finish'
                t_job.exec_output = '此任务没有指定执行服务器'
            t_job.end_time = timezone.now()
            settings.logger.info('{job} end run'.format(job=job_info))
            # 脚本执行完成

            if t_job.pause_when_finish:
                settings.logger.info('{job} need confirm'.format(job=job_info))
                t_job.pause_need_confirm = True
                t_job.save()
                TaskChange(task.id).send_change()
                TaskConfirm('{t_id}-{f_id}-{g_id}-{j_id}'.format(
                    t_id=str(task.id), f_id=str(t_flow.flow_id), g_id=t_group.group_id, j_id=t_job.job_id)
                ).wait_confirm()
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
