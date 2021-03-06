# coding=utf-8
from __future__ import absolute_import
from functools import reduce
from celery import shared_task
from celery.utils.log import get_task_logger
from celery.result import AsyncResult
from django.utils import timezone
from ActionSpace import settings
from om.proxy import Salt
from django.shortcuts import get_object_or_404, render
from django.core.mail import send_mail
from django.contrib.auth.models import User, Group as UG
from django.template import loader
from ast import literal_eval
import pika
import os
import re
import traceback
from django.db.models import Q

task_logger = get_task_logger(__name__)


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


def no_permission(request):
    settings.logger.info(request.user.username)
    return render(request, 'om/403.html')


@shared_task
def celery_send_mail(subject, msg, to):
    settings.logger.info(f'{subject}:{to}')
    if len(to) > 0:
        send_mail(subject=subject, message=msg, from_email=None, recipient_list=list(to), html_message=msg)
        return f'send mail to {to}'
    else:
        settings.logger.error('email list is None')
        return 'send mail to fail cause recipient is None'


def check_computer():
    from om.models import Computer, SaltMinion
    from django.db.models import Count
    last_return = {}

    count_not_one = list(Computer.objects.values('host').annotate(count=Count('host')).filter(count__gt=1).values('host', 'count'))
    if count_not_one:
        last_return['count_not_one'] = count_not_one
    change = []
    for minion in SaltMinion.objects.filter(status='up'):
        cpts = Computer.objects.filter(host__iexact=minion.host)
        if cpts.exists():
            cpt = cpts.first()
            ip_list = minion.ip_list.split(',')
            if cpt.ip not in ip_list:
                change.append({
                    'from': {'host': cpt.host, 'ip': cpt.ip, 'agent_name': cpt.agent_name},
                    'to': {'host': minion.host, 'ipv4': ip_list, 'agent_name': minion.name}
                })
    if change:
        last_return['change'] = change
    if not last_return:
        last_return['result'] = '没问题'
    return last_return


def update_from_salt(env_input=None):
    from om.models import SaltMinion, Computer, MacAddr
    from django.db.models import Subquery
    env_list = [env_input] if env_input is not None else ['PRD', 'UAT'] if settings.OM_ENV == 'PRD' else ['UAT']
    # SaltMinion.objects.all().delete()
    for env in env_list:
        try:
            result, back = Salt(env).grains('*', ['os', 'localhost', 'hwaddr_interfaces', 'ipv4', 'serialnumber'])
            if not result:
                settings.logger.error(back)
                settings.logger.error(f'{env} update_salt_manage_status fail')
                continue
            now = timezone.now()
            for ag_name, info in back['return'][0].items():
                ipv4_list = [x for x in info['ipv4'] if x not in ['127.0.0.1', '0.0.0.0']]
                minion, _ = SaltMinion.objects.get_or_create(name=ag_name, os=info['os'], env=env)
                minion.status = 'up'
                minion.update_time = now
                minion.host = info['localhost']
                minion.sn = info['serialnumber']
                minion.ip_list = ','.join(ipv4_list)
                minion.save()
                cpts = Computer.objects.filter(host__iexact=info['localhost'], env=env)
                cpts.update(
                    host=info['localhost'], agent_name=ag_name, installed_agent=True,
                    sys=Computer.get_sys(info['os']), update_time=now
                )
                if len(ipv4_list) == 1 and cpts.count() == 1:
                    if cpts.first().ip != ipv4_list[0]:
                        cpts.update(ip=ipv4_list[0], update_time=now)
                for eth, mac_addr in info['hwaddr_interfaces'].items():
                    MacAddr.objects.get_or_create(mac_hex=mac_addr, interface=eth, minion=minion, update_time=now)
            settings.logger.info(f'{env} update_salt_manage_status OK')
        except Exception as e:
            settings.logger.error(repr(e))
            settings.logger.error(f'{env} update_salt_manage_status fail')
            settings.logger.error(traceback.format_exc())
    # Computer.objects.only('agent_name').filter(agent_name__in=Subquery(SaltMinion.objects.filter(status='up').values('name'))).update(installed_agent=True)
    Computer.objects.only('agent_name').exclude(agent_name__in=Subquery(SaltMinion.objects.filter(status='up').values('name'))).update(installed_agent=False)
    # MacAddr.objects.filter(minion__name__in=Subquery(SaltMinion.objects.filter(status='up').values('name'))).delete()


def str2arr(val, sep=',', digit_check=True):
    arr = []
    if val:
        arr = [x.strip() for x in val.split(sep) if not digit_check or x.isdigit()]
    return arr


def get_task_result(result_id):
    return AsyncResult(result_id)


def get_agent_info(agent_name):
    settings.logger.info(agent_name)
    from om.models import SaltMinion
    for agent in SaltMinion.objects.filter(name=agent_name):
        result, back = Salt('PRD' if agent.env == 'PRD' else 'UAT').grains(agent_name)
        if not result:
            settings.logger.error(repr(back))
        return back if result else {'result': '获取失败'}
    else:
        return {'result': 'agent不存在'}


def get_name(content):
    if isinstance(content, bytes):
        return content.decode()
    else:
        return content


def expand_server_list(post_form):
    from om.models import ComputerGroup
    server_list = set([])
    for s in post_form.getlist('server_list'):
        if s.startswith('group-'):
            for cg in ComputerGroup.objects.filter(pk=s.replace('group-', '')):
                server_list = server_list.union(cg.computer_list.values_list('id', flat=True))
        else:
            server_list.add(s)
    for group_id in post_form.getlist('server_group_list'):
        server_list = server_list.union(ComputerGroup.objects.get(pk=group_id).computer_list.values_list('id', flat=True))
    form_data = post_form.copy()
    form_data.setlist('server_list', list(server_list))
    return form_data


def fmt_salt_out(val, replace=True):
    replace_list = [
        ("[{'", ''), ("'}]", "'"), ("', '", "', \n"), ("': '", ": \n'"), ("'}, '", "'}, \n"),
        (r'\r\n', '\n '), (r'\t', '\t'), (r'\n', '\n '), (r'\r', ''), (r'\x1b[7l', '')
    ]
    if isinstance(val, dict):
        content = val.get('return', val)
    else:
        content = val
    content = repr(content)
    if replace:
        for ora, new in replace_list:
            content = content.replace(ora, new)
    return content


def clone_task(task, username, auto=False):
    from om.models import Task, TaskFlow, TaskJobGroup, TaskJob
    t_flow = task.taskflow_set.first()
    new_t_task = Task.objects.create(
        name=task.name, founder=username, approval_time=timezone.now(),
        async_result='auto' if auto else '', recipient=task.recipient
    )
    new_t_flow = TaskFlow.objects.create(name=t_flow.name, flow_id=t_flow.flow_id, task=new_t_task)
    group_list_array = t_flow.taskjobgroup_set.all()
    settings.logger.info('clone_group_list:[{gl}], new_t_flow_id:{new_t_flow_id}'.format(
        gl=repr([x.pk for x in group_list_array]), new_t_flow_id=t_flow.pk
    ))
    for task_group in group_list_array:
        t_group = TaskJobGroup.objects.create(
            name=task_group.name, group_id=task_group.group_id,
            flow=new_t_flow, step=task_group.step
        )
        job_list_array = task_group.taskjob_set.all()
        settings.logger.info('clone_job_list:[{gl}], t_group_id:{t_group_id}'.format(
            gl=repr([x.pk for x in job_list_array]), t_group_id=t_group.pk
        ))
        for task_job in job_list_array:
            TaskJob.objects.create(
                name=task_job.name, job_id=task_job.job_id, group=t_group, job_type=task_job.job_type,
                script_type=task_job.script_type, script_content=task_job.script_content,
                begin_time=timezone.now(), end_time=timezone.now(), status='no_run',
                file_name=task_job.file_name, target_name=task_job.target_name,
                pause_when_finish=task_job.pause_when_finish, script_param=task_job.script_param,
                server_list=task_job.server_list, pause_finish_tip=task_job.pause_finish_tip,
                exec_user=task_job.exec_user, exec_output='', step=task_job.step
            )
    new_t_task.save()
    return new_t_task


def make_task(username, flow_id, job_id):
    from om.models import Job, JobGroup, Flow, Task, TaskFlow, TaskJobGroup, TaskJob
    if flow_id == -1 and job_id != -1:  # flow不存在， job存在说明是快速执行任务来的
        job = get_object_or_404(Job, pk=job_id)
        group = JobGroup.objects.create(name='临时组', job_list=str(job.id))
        flow = Flow.objects.create(is_quick_flow=True, job_group_list=str(group.id))
    else:
        flow = get_object_or_404(Flow, pk=flow_id)

    task = Task.objects.create(name=flow.name, founder=username, approval_time=timezone.now(), recipient=flow.recipient)
    t_flow = TaskFlow.objects.create(name=flow.name, flow_id=flow.pk, task=task)
    group_list_array = str2arr(flow.job_group_list)
    settings.logger.info('group_list:[{ora_gl}]->[{end_gl}], flow_id:{flow_id}'.format(
        ora_gl=repr(flow.job_group_list), end_gl=repr(group_list_array),
        flow_id=t_flow.pk
    ))
    for i_group, group_id in enumerate(group_list_array):
        group = get_object_or_404(JobGroup, pk=group_id)
        t_group = TaskJobGroup.objects.create(name=group.name, group_id=group.pk, flow=t_flow, step=i_group)
        job_list_array = str2arr(group.job_list)
        settings.logger.info('job_list:[{ora_gl}]->[{end_gl}], group_id:{group_id}'.format(
            ora_gl=repr(group.job_list), end_gl=repr(job_list_array), group_id=t_group.pk
        ))
        for i_job, job_id in enumerate(job_list_array):
            job = get_object_or_404(Job, pk=job_id)
            server_ip_list = ','.join([x.ip for x in job.server_list.all()])
            file_name_list = ','.join([str(x.id) for x in job.file_name.all()])
            TaskJob.objects.create(
                name=job.name, job_id=job.pk, group=t_group, job_type=job.job_type,
                script_type=job.script_type, script_content=job.script_content,
                begin_time=timezone.now(), end_time=timezone.now(), status='no_run',
                pause_when_finish=job.pause_when_finish, script_param=job.script_param,
                file_name=file_name_list, target_name=job.target_name,
                exec_user=job.exec_user, server_list=server_ip_list,
                pause_finish_tip=job.pause_finish_tip, exec_output='', step=i_job
            )
    task.save()
    return task


def quick_script_exec(job, username):
    from om.models import Flow, JobGroup
    group = JobGroup.objects.create(
        name='快速执行脚本:' + job.name, founder=username,
        last_modified_by=username, job_list=str(job.id)
    )
    prefix = '快速执行脚本:' if job.job_type == 'SCRIPT' else '快速分发文件:'
    flow = Flow.objects.create(name=prefix + job.name, is_quick_flow=True, job_group_list=str(group.id))
    return make_task(username, flow.id, job.id)


class JobCallback(object):
    def __init__(self, info, msg):
        self.info = info
        from collections import OrderedDict
        self.groups = OrderedDict()
        reg = r'\[\[(?P<action>[a-z]+)\|(?P<arg>([\u2E80-\u9FFF]|.)*?)\]\]'
        # 示例：
        # [[mail | {'to': 'weiquanzu603@pingan.com.cn', 'subject': '邮件主题', 'message': '邮件内容'}]]
        # [[confirm | {'message': '消息'}]]
        last_msg = repr(msg).replace('\n', '').replace('\r', '')
        for val in re.finditer(reg, 'last_msg:' + last_msg):
            try:
                action = val.group('action')
                if action is not None:
                    arg = val.group('arg')
                    parse = literal_eval(arg)
                    if isinstance(parse, dict):
                        self.groups[action] = parse
                else:
                    settings.logger.error('action is None')
            except Exception as e:
                self.reason = '语法错误'
                settings.logger.error(repr(e))
                settings.logger.error(traceback.format_exc())

    def run(self, job):
        from om.worker import ActionDetailConsumer
        for action, content in self.groups.items():
            if action == 'mail':  # mail:发邮件
                to = content.get('to')
                subject = content.get('subject')
                message = content.get('message')
                if all([to, subject, message]):
                    settings.logger.info('job mail')
                    celery_send_mail(subject, message, to.split())
                else:
                    settings.logger.info('job have None in [to, subject, message]')
            elif action == 'confirm':  # confirm:JOB执行完成后暂停等待用户确认后再继续
                if not job.pause_when_finish:
                    settings.logger.info('job confirm')
                    message = content.get('message')
                    ora_message = job.pause_finish_tip
                    if message is not None:
                        job.pause_finish_tip = message
                    job.pause_need_confirm = True
                    job.save()
                    ActionDetailConsumer.task_change(self.info.split('-')[0])
                    TaskConfirm(self.info).wait_confirm()
                    job.pause_need_confirm = False
                    job.pause_finish_tip = ora_message
                    job.save()
                else:
                    settings.logger.info('job already pause_when_finish')
            else:
                settings.logger.warn('unknown action:{ac}'.format(ac=action))


# noinspection PyUnresolvedReferences
class JobExec(object):
    def __init__(self, job, job_key, ips, om_env):
        self.job = job
        self.job_key = job_key
        self.ips = ips
        self.om_env = om_env
        self.first = True

    def set_job_output(self, val):
        if self.first:
            self.job.exec_output = ''
        else:
            self.job.exec_output += '\n'
        self.job.exec_output += val if isinstance(val, str) else repr(val)

    def loop(self):
        from om.models import Computer
        cpt = Computer.objects.filter(ip__in=self.ips)
        cpt_prd = cpt.filter(env='PRD')
        cpt_uat = cpt.exclude(env='PRD')
        param_list = []
        if self.om_env == 'PRD':
            param_list.append({'env': 'PRD', 'sys': 'windows', 'agents': cpt_prd.filter(sys='windows')})
            param_list.append({'env': 'PRD', 'sys': 'linux', 'agents': cpt_prd.exclude(sys='windows')})
        param_list.append({'env': 'UAT', 'sys': 'windows', 'agents': cpt_uat.filter(sys='windows')})
        param_list.append({'env': 'UAT', 'sys': 'linux', 'agents': cpt_uat.exclude(sys='windows')})
        for i, v in enumerate(param_list):
            self.first = i == 0
            self.exec_job(**v)

    def process_script(self, salt, sys, agents):
        agents_list = list(agents.values_list('agent_name', flat=True))
        if self.job.script_type in ['SHELL', 'BAT']:
            if sys == 'windows':
                salt_result, salt_output = salt.windows_batch(
                    agents_list, self.job.script_content, self.job.script_param
                )
            else:
                salt_result, salt_output = salt.linux_shell(
                    agents_list, self.job.script_content, self.job.script_param, self.job.exec_user
                )
        elif self.job.script_type == 'PY':
            salt_result, salt_output = salt.python(agents_list, self.job.script_content)
        else:
            assert False, f'Unsupported script_type:{self.job.script_type}'
        self.job.status = 'finish' if salt_result else 'run_fail'
        self.set_job_output(fmt_salt_out(salt_output))
        JobCallback(self.job_key, salt_output)

    def process_file(self, salt, sys, agents):
        from om.models import ServerFile
        agents_list = list(agents.values_list('agent_name', flat=True))
        file_list = [ServerFile.objects.get(pk=x).name for x in str2arr(self.job.file_name)]
        if len(file_list) == 0:
            self.job.status = 'run_fail'
            self.job.exec_output = '没有指定要传输的文件'
        else:
            result_list = []
            output_list = []
            for file_to_trans in file_list:
                if self.job.target_name.endswith('\\') or self.job.target_name.endswith('/'):
                    target_path = os.path.join(self.job.target_name, file_to_trans)
                else:
                    target_path = self.job.target_name
                salt_result, salt_output = salt.file_trans(agents_list, file_to_trans, target_path)
                if sys != 'windows':
                    salt.shell(agents_list, 'chown {0}:{0} {1}'.format(self.job.exec_user, target_path), 'root')
                result_list.append(salt_result)
                output_list.append(salt_output)
                if not salt_result:
                    settings.logger.error()
            self.job.status = 'finish' if all(result_list) else 'run_fail'
            self.set_job_output(output_list)
            JobCallback(self.job_key, output_list)

    def exec_job(self, env, sys, agents):
        if len(agents) == 0:
            settings.logger.warn(f'agents is empty for {env}:{sys}')
            return
        try:
            if self.job.job_type == 'SCRIPT':
                self.process_script(Salt(env), sys, agents)
            elif self.job.job_type == 'FILE':
                self.process_file(Salt(env), sys, agents)
            else:
                assert False, f'Unsupported job_type:{self.job.job_type}'
        except Exception as e:
            self.job.status = 'run_fail'
            settings.logger.error(str(e))
            settings.logger.error(traceback.format_exc())
            self.job.exec_output = f'执行出错，请检查作业配置是否有误！'


def get_recipient(task, sender):
    email = None
    try:
        if task.recipient is not None and task.recipient.user_list.exists():
            email = task.recipient.user_list.values_list('email', flat=True)
        else:
            email = [User.objects.get(username=sender).email]
    except User.DoesNotExist as e:
        try:
            email = [x.email for x in UG.objects.get(name='应用服务二组').user_set.all()]
        except UG.DoesNotExist as ge:
            settings.logger.error(repr(ge))
        settings.logger.error(repr(e))
    except Exception as e:
        settings.logger.error(repr(e))
    settings.logger.info(repr(email))
    return email


def exec_task(tid, sender):
    from om.models import Task
    from om.worker import ActionDetailConsumer
    task_logger.info('user=[%s], task_id=[%d]' % (sender, tid))
    settings.logger.info('celery_exec_task: user=[%s], task_id=[%d]' % (sender, tid))
    task = Task.objects.get(pk=tid)
    task.exec_user = sender
    t_flow = task.taskflow_set.first()
    task.run()
    show_info = []
    for t_group in t_flow.taskjobgroup_set.all().order_by('step'):
        for t_job in t_group.taskjob_set.all().order_by('step'):
            t_job.begin_time = timezone.now()
            t_job.status = 'running'
            t_job.save()
            ActionDetailConsumer.task_change(task.id)
            job_info = 'task_id[{tid}]:flow {f_id}], group {g_id}, {g_step}], job {j_id}, {j_step}]'.format(
                tid=task.id, f_id=t_flow.flow_id, g_id=t_group.group_id, g_step=t_group.step,
                j_id=t_job.job_id, j_step=t_job.step
            )

            # 脚本开始执行
            settings.logger.info('{job} begin run'.format(job=job_info))
            ips = str2arr(t_job.server_list, digit_check=False)

            job_id_info = '{t_id}-{f_id}-{g_id}-{j_id}'.format(
                t_id=str(task.id), f_id=str(t_flow.flow_id), g_id=t_group.group_id, j_id=t_job.job_id
            )

            if len(ips) > 0:
                JobExec(t_job, job_id_info, ips, settings.OM_ENV).loop()
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
                ActionDetailConsumer.task_change(task.id)
                TaskConfirm(job_id_info).wait_confirm()
                t_job.pause_need_confirm = False
                t_job.save()
            else:
                t_job.save()
                ActionDetailConsumer.task_change(task.id)
            show_info.append({'name': t_job.name, 'output': t_job.exec_output})
    task.finish()
    ActionDetailConsumer.task_change(task.id)
    email = get_recipient(task, sender)
    email_msg = loader.render_to_string('om/email.html', {'tid': task.id, 'name': t_flow.name, 'info': show_info})
    settings.logger.info('celery_send_mail to email={mail}'.format(mail=email))
    celery_send_mail(t_flow.name if t_flow and t_flow.name else 'OM 运维工作平台 消息通知', email_msg, email)
    return f'[{tid}]执行完成'


def task_from_args(arg):
    from om.models import Task
    arg_list = literal_eval(arg)
    task = None
    if isinstance(arg_list, list) and len(arg_list) == 2:
        try:
            task = Task.objects.get(pk=arg_list[0])
        except Task.DoesNotExist as _:
            task = None
    return task


def reset_task(tid):
    from om.models import Task
    task = Task.objects.get(pk=tid)
    t_flow = task.taskflow_set.first()
    for t_group in t_flow.taskjobgroup_set.all().order_by('step'):
        for t_job in t_group.taskjob_set.all().order_by('step'):
            t_job.status = 'no_run'
            t_job.save()
    task.status = 'no_run'
    task.async_result = ''
    task.save()


def monkey_exec_task(tid, sender):
    from om.worker import ActionDetailConsumer
    from om.models import Task
    import time
    reset_task(tid)
    task = Task.objects.get(pk=tid)
    task.exec_user = sender
    t_flow = task.taskflow_set.first()
    task.run()
    for t_group in t_flow.taskjobgroup_set.all().order_by('step'):
        for t_job in t_group.taskjob_set.all().order_by('step'):
            t_job.begin_time = timezone.now()
            t_job.status = 'running'
            t_job.save()
            time.sleep(5)
            ActionDetailConsumer.task_change(task.id)
            t_job.status = 'finish'
            t_job.end_time = timezone.now()
            t_job.save()
            ActionDetailConsumer.task_change(task.id)
        time.sleep(5)
    task.finish()
    task.save()
    ActionDetailConsumer.task_change(task.id)
    return u'[{id}]执行完成'.format(id=tid)


@shared_task
def celery_exec_task(tid, sender):
    return exec_task(tid, sender) if True else monkey_exec_task(tid, sender)


@shared_task
def celery_auto_task(tid, sender):
    from om.models import Task
    new_task = clone_task(Task.objects.get(pk=tid), '自动', True)
    # new_task.async_result = self.id
    new_task.approval('自动', 'Y', '自动审核通过')
    return exec_task(new_task.id, sender)


def get_paged_query(query, search_fields, request, force_order=None):
    settings.logger.info(repr(request.GET))
    try:
        ordering = []
        search = request.GET.get('search')
        offset = request.GET.get('offset')
        offset = 0 if offset is None else int(offset)
        limit = request.GET.get('limit')
        limit = 5 if limit is None else int(limit)
        sort_val = request.GET.get('sort')
        order = request.GET.get('order')
        if all([sort_val, order]):
            ordering.append('-' + sort_val if order == 'desc' else sort_val)
        if force_order is not None and force_order.lower() != 'pk':
            ordering.append(force_order)
        ordering.append('pk')
        query = query.order_by(*ordering)
        if search is not None:
            select = Q()
            multi = len(search_fields) > 1
            s_1st = search_fields[0]
            s_other = search_fields[1:]
            search_mode = 'and'
            if ':' in search:
                search_info = search.split(':')
                search_mode = search_info[0]
                search_keys = ' '.join(search_info[1:]).split()
            else:
                search_keys = search.split()
            for t in search_keys:
                q_1st = Q(**{s_1st: t})
                this_run = reduce(lambda x, y: x | Q(**{y: t}), s_other, q_1st) if multi else q_1st
                if search_mode.lower() == 'or':
                    select |= this_run
                else:
                    select &= this_run
            settings.logger.info(repr(select))
            query = query.filter(select).distinct()
        query_count = query.count()
        settings.logger.info(f'query[{offset}: {min(offset + limit, query_count)}], {query_count}')
        return query[offset: min(offset + limit, query_count)], query_count
    except Exception as e:
        settings.logger.error(repr(e))
        if request.user.is_superuser:
            return query, query.count()
        else:
            return query[0:0], 0


def add_cpt(system_name, entity_name, ip, host, env_type, sys_type, installed_agent=False, desc=''):
    from om.models import System, Entity, Computer
    # print(system_name, entity_name, ip, host, env_type, sys_type, installed_agent, desc)
    if env_type not in [x[0] for x in Computer.ENV_TYPE]:
        return 'invalid env'
    if sys_type not in [x[0] for x in Computer.SYS_TYPE]:
        return 'invalid sys_type'
    system_obj, system_created = System.objects.get_or_create(name=system_name)
    if system_created:
        settings.logger.info(f'system created:{system_name},{desc}')
    entity_obj, entity_created = Entity.objects.get_or_create(name=entity_name, system=system_obj)
    if entity_created:
        settings.logger.info(f'entity created:{entity_name},system:{system_obj.name},{desc}')
    computer_obj, computer_created = Computer.objects.get_or_create(
        ip=ip, env=env_type
    )
    if computer_created:
        settings.logger.info(f'computer created:{ip}, {host}, {sys_type}, {env_type},{desc}')
        computer_obj.host = host
        computer_obj.sys = sys_type
        computer_obj.installed_agent = installed_agent
        computer_obj.desc = desc
        computer_obj.save()
    computer_obj.entity.add(entity_obj)


def import_detector(url='detector_url'):
    import requests
    result = requests.get(url=url)
    for ele in result.json():
        system_name = ele['site']
        entity_name = ele['pool']
        ip = ele['ip']
        host = ele['hostname']
        env_type = 'PRD' if ele['env'] in ['Production', 'DR'] else ele['env']
        sys_type = ele['system'].lower()
        # print(f'async from detector:{system_name}, {entity_name}, {ip}, {host}, {env_type}, {sys_type}')
        add_cpt(system_name, entity_name, ip, host, env_type, sys_type, desc='from detector')


def import_prism(url='prism_url'):
    import requests
    result = requests.get(url=url)
    r_json = result.json()
    if 'results' not in r_json:
        return
    for ele in r_json['results']:
        arr = ele['name'].split('-')
        ip = arr[-1]
        host = '-'.join(arr[0:-1])
        env_type = ele['server_env']
        if 'server_sys' not in ele:
            continue
        sys_type = ele['server_sys'].lower()
        for entity_url in ele['ip_subserver']:
            subserver_result = requests.get(url=entity_url)
            sub_json = subserver_result.json()
            if 'app_name' not in sub_json:
                continue
            app_result = requests.get(url=sub_json['app_name'])
            app_json = app_result.json()
            if 'name' not in app_json:
                continue
            entity_name = app_json['name']
            if 'site_app' not in app_json:
                continue
            site_app_url = app_json['site_app']
            if len(site_app_url) != 1:
                print(arr, site_app_url)
                continue
            system_result = requests.get(url=site_app_url[0])
            system_json = system_result.json()
            if 'name' not in system_json:
                continue
            system_name = system_json['name']
            # print(f'async from prism:{system_name}, {entity_name}, {ip}, {host}, {env_type}, {sys_type}')
            add_cpt(system_name, entity_name, ip, host, env_type, sys_type, True, desc='from prism')

    next_url = r_json['next']
    if next_url is not None:
        import_prism(next_url)


def syn_data_outside():
    import_detector()
    import_prism()


def get_task_computers_list(user):
    from om.models import Computer
    if user.is_superuser:
        query = Computer.objects.select_related().all()
    else:
        from guardian.shortcuts import get_objects_for_user
        pk_set = set([])
        # 1、获取所有按系统授权的主机
        for sys in get_objects_for_user(user, 'om.can_task_system'):
            for ent in sys.entity_set.all():
                pk_set |= set(list(ent.computer_set.values_list('pk', flat=True)))
        # 2、获取所有按逻辑实体授权的主机
        for ent in get_objects_for_user(user, 'om.can_task_entity'):
            pk_set |= set(list(ent.computer_set.values_list('pk', flat=True)))
        # 3、获取所有按主机授权的主机
        cpt_list = get_objects_for_user(user, 'om.can_task_computer')
        pk_set |= set(list(cpt_list.values_list('pk', flat=True)))
        query = Computer.objects.select_related().filter(pk__in=pk_set)
    return query


def api_server_list(request, only_for_task=False):
    from om.models import Computer
    search_fields = [
        'pk__icontains', 'host__icontains', 'ip__icontains', 'env__icontains',
        'sys__icontains', 'agent_name__icontains', 'entity__name__icontains'
    ]
    if only_for_task:
        query = get_task_computers_list(request.user)
    else:
        query = Computer.objects.select_related()
    computers, computer_count = get_paged_query(query, search_fields, request)
    result = {'total': computer_count, 'rows': []}
    [result['rows'].append({
        'id': c.id,
        'env': c.env,
        'entity_name': c.entity_name(),
        'sys': c.sys,
        'installed_agent': '是' if c.installed_agent else '否',
        'agent_name': c.agent_name,
        'ip': c.ip,
        'host': c.host
    }) for c in computers]
    return result


def task_in_prd(tid):
    from om.models import Task, Computer
    try:
        t_flow = Task.objects.get(pk=tid).taskflow_set.first()
        for t_group in t_flow.taskjobgroup_set.all().order_by('step'):
            for t_job in t_group.taskjob_set.all().order_by('step'):
                if Computer.objects.filter(ip__in=str2arr(t_job.server_list, digit_check=False), env='PRD').exists():
                    return True
    except Task.DoesNotExist as e:
        settings.logger.error(repr(e))
        return False
    return False


def check_cpt_ping(cpt_id):
    from om.models import Computer
    cpt = Computer.objects.get(pk=cpt_id)
    result, back = Salt('PRD' if cpt.env == 'PRD' else 'UAT').ping([cpt.agent_name])
    ping_success = back['return'][0].get(cpt.agent_name, False)
    if ping_success != cpt.installed_agent:
        cpt.installed_agent = ping_success
        cpt.save()
    return result and ping_success


def check_minion_ping(minion_id):
    from om.models import SaltMinion
    minion = SaltMinion.objects.get(pk=minion_id)
    result, back = Salt('PRD' if minion.env == 'PRD' else 'UAT').ping([minion.name])
    ping_success = back['return'][0].get(minion.name, False)
    if ping_success != (minion.status == 'up'):
        minion.status = 'up' if ping_success else 'down'
        minion.save()
    return result and ping_success


def ip_in_salt_minion(ip):
    from om.models import SaltMinion
    minions = SaltMinion.objects.only('ip_list').filter(ip_list__contains=ip, status='up')
    return len([x for x in minions if ip in x.ip_list.split(',')]) > 0


def host_in_salt_minion(host):
    from om.models import SaltMinion
    return SaltMinion.objects.only('ip_list').filter(host=host, status='up').exists()


@shared_task
def switch_task():
    from switch.util import Scan
    Scan(True).run()


@shared_task
def cmdb_task(update_time, action_id, callback=None):
    from cmdb.util import update_computer
    update_computer(update_time, action_id, callback)
