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
import uuid
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
    send_mail(subject=subject, message=msg, from_email=None, recipient_list=to, html_message=msg)
    return 'send mail to {to}'.format(to=to)


def update_salt_manage_status(env_input=None):
    from om.models import SaltMinion
    if env_input is None:
        env_list = ['UAT']
        if settings.OM_ENV == 'PRD':
            env_list.append('PRD')
    else:
        env_list = [env_input]

    for env in env_list:
        SaltMinion.objects.filter(env=env).delete()
        result, back = Salt(env).manage_status()
        if result:
            total = back['return'][0]
            for status in total.keys():
                for agent in total[status]:
                    ag, _ = SaltMinion.objects.get_or_create(name=agent, env=env)
                    ag.status = status
                    ag.update_time = timezone.now()
                    ag.save()
                settings.logger.info('{st}:{ct}'.format(st=status, ct=len(total[status])))
            settings.logger.info('{env} OK'.format(env=env))
        else:
            settings.logger.error('fail')
        result, back = Salt(env).os_type()
        if result:
            total = back['return'][0]
            for agent, os_type in total.items():
                minions = SaltMinion.objects.filter(name=agent, env=env)
                for minion in minions:
                    minion.os = os_type['os']
                    minion.save()


def sync_computer_agent_name():
    from om.models import Computer, SaltMinion
    for agent in SaltMinion.objects.all():
        ag_ip = agent.name.split('-')[-1]
        for cp in Computer.objects.filter(ip=ag_ip):
            cp.agent_name = agent.name
            cp.installed_agent = agent.status == 'up'
            cp.save()


def sync_computer_sys_type(env_input=None):
    from om.models import Computer
    if env_input is None:
        env_list = ['UAT']
        if settings.OM_ENV == 'PRD':
            env_list.append('PRD')
    else:
        env_list = [env_input]
    for env in env_list:
        result, back = Salt(env).os_type()
        if result:
            total = back['return'][0]
            for agent, info in total.items():
                for cp in Computer.objects.filter(agent_name=agent):
                    cp.sys = 'windows' if info['os'] == 'Windows' else 'linux'
                    cp.save()
        else:
            settings.logger.error('fail')


def sync_mac_address(env_input=None):
    from om.models import SaltMinion, MacAddr
    if env_input is None:
        env_list = ['UAT']
        if settings.OM_ENV == 'PRD':
            env_list.append('PRD')
    else:
        env_list = [env_input]
    MacAddr.objects.all().delete()
    for env in env_list:
        result, back = Salt(env).hwaddr_interfaces()
        if result:
            for name, mac in back['return'][0].items():
                try:
                    minion = SaltMinion.objects.get(name=name, env=env)
                    for eth, mac_addr in mac['hwaddr_interfaces'].items():
                        if mac_addr.strip() not in ['0.0.0.0', '00:00:00:00:00:00']:
                            MacAddr.objects.get_or_create(mac_hex=mac_addr, interface=eth, minion=minion)
                except SaltMinion.DoesNotExist as _:
                    print('DoesNotExist:{name}, env:{env}'.format(name=name, env=env))
                except SaltMinion.MultipleObjectsReturned as _:
                    print('MultipleObjectsReturned:{name}, info:{info}, env:{env}'.format(
                        name=name, info=SaltMinion.objects.filter(name=name), env=env
                    ))
        else:
            settings.logger.error('fail')


def salt_all(env=None):
    update_salt_manage_status(env)
    sync_computer_agent_name()
    sync_computer_sys_type(env)
    sync_mac_address(env)


def str2arr(val, sep=',', digit_check=True):
    arr = []
    if val:
        arr = [x for x in val.split(sep) if not digit_check or x.isdigit()]
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


def get_salt_status():
    return Salt(settings.OM_ENV).manage_status()


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
        ("[{'", ''), ("'}]", "'"), ("', '", "', \n"), ("': '", ":\n'"),
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
        async_result='auto' if auto else ''
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

    task = Task.objects.create(name=flow.name, founder=username, approval_time=timezone.now())
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


def exec_task_job(t_job, ips, env):
    from om.models import Computer, ServerFile
    ora_output = {}
    if len(ips) == 0:
        settings.logger.warn('ips is empty for {env}'.format(env=env))
        # t_job.exec_output = '指定的IP无效！'
        # t_job.status = 'run_fail'
        return
    if env == 'PRD':
        agents = list(Computer.objects.filter(env='PRD', ip__in=ips).values_list('agent_name', flat=True))
    else:
        agents = list(Computer.objects.exclude(env='PRD').filter(ip__in=ips).values_list('agent_name', flat=True))
    if len(agents) == 0:
        settings.logger.warn('agents is empty for {env}'.format(env=env))
        # t_job.status = 'run_fail'
        # t_job.exec_output = '指定的IP不符合当前环境！'
        return
    is_windows = Computer.objects.get(agent_name=agents[0]).sys == 'windows'
    settings.logger.info('{env} agents:{ag}'.format(env=env, ag=agents))
    cmd = t_job.script_content
    if t_job.job_type == 'SCRIPT':
        if not is_windows and t_job.script_type == 'SHELL':
            cmd = t_job.script_content
            dos2unix = cmd.replace('\r\n', '\n')
            dos2unix = dos2unix.replace("'", r"'\''")
            def_shell = '' if cmd.startswith('#!') else "#!/bin/bash\n"
            tmp_file = '/tmp/{n}.sh'.format(n=uuid.uuid4())
            cmd = '''echo '{shell}{content}
'>"{tg}";chmod u+x "{tg}";"{tg}"'''.format(shell=def_shell, content=dos2unix, tg=tmp_file)
            if t_job.script_param.strip() != '':
                cmd += ' {param}'.format(param=t_job.script_param)
            delete_after_exec = True
            if delete_after_exec:
                cmd += ';[ -f "{tg}" ] && rm -f "{tg}"'.format(tg=tmp_file)
        else:
            cmd = ' '.join([t_job.script_content, t_job.script_param])
    try:
        if t_job.job_type == 'SCRIPT':
            if t_job.script_type == 'PY':
                salt_result, salt_output = Salt(env).python(agents, cmd)
            else:
                exec_user = None if is_windows or t_job.script_type == 'BAT' else t_job.exec_user
                salt_result, salt_output = Salt(env).shell(agents, cmd, exec_user)
            t_job.status = 'finish' if salt_result else 'run_fail'
            ora_output = salt_output
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
                    salt_result, salt_output = Salt(env).file_trans(agents, file_to_trans, target_path)
                    if not is_windows:
                        Salt(env).shell(agents, 'chown {0}:{0} {1}'.format(t_job.exec_user, target_path), 'root')
                    result_list.append(salt_result)
                    output_list.append(salt_output)
                    if not salt_result:
                        settings.logger.error()
                t_job.status = 'finish' if all(result_list) else 'run_fail'
                ora_output = output_list
                t_job.exec_output = fmt_salt_out(output_list)
    except Exception as e:
        t_job.status = 'run_fail'
        settings.logger.error(str(e))
        settings.logger.error(traceback.format_exc())
        t_job.exec_output = '执行出错，请检查作业配置是否有误！'
    return ora_output


class JobCallback(object):
    def __init__(self, info, msg):
        self.info = info
        from collections import OrderedDict
        self.groups = OrderedDict()
        reg = r'\[\[(?P<action>[a-z]+)\|(?P<arg>([\u2E80-\u9FFF]|.)*?)\]\]'
        # 示例：
        # [[mail | {'to': 'weiquanzu603@pingan.com.cn', 'subject': '邮件主题', 'message': '邮件内容'}]]
        # [[confirm | {'message': '消息'}]]
        last_msg = msg.replace('\n', '').replace('\r', '')
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


def exec_task(tid, sender):
    from om.models import Task
    from om.worker import ActionDetailConsumer
    task_logger.info('user=[%s], task_id=[%d]' % (sender, tid))
    settings.logger.info('celery_exec_task: user=[%s], task_id=[%d]' % (sender, tid))
    task = Task.objects.get(pk=tid)
    task.exec_user = sender
    t_flow = task.taskflow_set.first()
    task.run()
    email = None
    try:
        email = [User.objects.get(username=sender).email]
    except User.DoesNotExist as e:
        try:
            email = [x.email for x in UG.objects.get(name='应用服务二组').user_set.all()]
        except UG.DoesNotExist as ge:
            settings.logger.error(repr(ge))
        settings.logger.error(repr(e))
    except Exception as e:
        settings.logger.error(repr(e))
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
                if settings.OM_ENV == 'PRD':
                    ora_prd_output = exec_task_job(t_job, ips, 'PRD')
                    JobCallback(job_id_info, fmt_salt_out(ora_prd_output, False)).run(t_job)
                ora_uat_output = exec_task_job(t_job, ips, 'UAT')
                JobCallback(job_id_info, fmt_salt_out(ora_uat_output, False)).run(t_job)
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
            if email is not None:
                show_info.append({'name': t_job.name, 'output': t_job.exec_output})
    task.finish()
    task.save()
    ActionDetailConsumer.task_change(task.id)
    settings.logger.info('email:{email}'.format(email=email))
    if email is not None:
        email_msg = loader.render_to_string('om/email.html', {'tid': task.id, 'name': t_flow.name, 'info': show_info})
        settings.logger.info('celery_send_mail to email={mail}'.format(mail=email))
        # celery_send_mail('OM 运维工作平台 消息通知', email_msg, email)
        subject = 'OM 运维工作平台 消息通知'
        if t_flow and t_flow.name:
            subject = t_flow.name
        celery_send_mail(subject, email_msg, email)
    return u'[{id}]执行完成'.format(id=tid)


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
        search = request.GET.get('search')
        if force_order is not None:
            query = query.order_by(force_order)
        offset = int(request.GET.get('offset'))
        limit = int(request.GET.get('limit'))
        sort_val = request.GET.get('sort')
        order = request.GET.get('order')
        if all([sort_val, order]):
            query = query.order_by('-'+sort_val if order == 'desc' else sort_val)
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
        return query[int(offset): min(offset + limit, query_count)], query_count
    except Exception as e:
        settings.logger.error(repr(e))
        if request.user.is_superuser:
            return query, query.count()
        else:
            return query[0:0], 0


def add_cpt(system_name, entity_name, ip, host, env_type, sys_type, installed_agent=False, desc=''):
    from om.models import System, Entity, Computer
    if env_type not in [x[0] for x in Computer.ENV_TYPE]:
        return 'invalid env'
    if sys_type not in [x[0] for x in Computer.SYS_TYPE]:
        return 'invalid sys_type'
    system_obj, system_created = System.objects.get_or_create(name=system_name)
    entity_obj, entity_created = Entity.objects.get_or_create(name=entity_name, system=system_obj)
    computer_obj, computer_created = Computer.objects.get_or_create(
        ip=ip, env=env_type
    )
    if computer_created:
        computer_obj.host = host
        computer_obj.sys = sys_type
        computer_obj.installed_agent = installed_agent
        computer_obj.desc = desc
    computer_obj.entity.add(entity_obj)
    return ''


def import_detector():
    import requests
    result = requests.get(url='http://detectorip:port/detector_api')
    for ele in result.json():
        system_name = ele['site']
        entity_name = ele['pool']
        ip = ele['ip']
        host = ele['hostname']
        env_type = 'PRD' if ele['env'] == 'Production' else ele['env']
        sys_type = ele['system'].lower()
        add_cpt(system_name, entity_name, ip, host, env_type, sys_type)
