# coding=utf-8
from __future__ import print_function

from ActionSpace import settings
from om.util import update_from_salt, syn_data_outside, fmt_salt_out, check_computer
from om.models import CallLog
from django.contrib.auth.models import User, AnonymousUser
from om.proxy import Salt
from channels.generic.websockets import JsonWebsocketConsumer
from om.models import SaltMinion
from utils.util import CheckFireWall
import traceback
import re


class OmConsumer(JsonWebsocketConsumer):
    http_user = True

    def raw_connect(self, message, **kwargs):
        user = 'unknown'
        # noinspection PyBroadException
        try:
            not_login_user = User.objects.get_or_create(username='not_login_yet', is_active=False)[0]
            user = not_login_user if isinstance(message.user, AnonymousUser) else message.user
        except Exception as e:
            settings.logger.error(repr(e))
        CallLog.objects.create(
            user=user,
            type='message',
            action=message['path'],
            detail=message.content
        )
        settings.logger.info('recv_data:{data}'.format(data=message.content, path=message['path']))
        super(OmConsumer, self).raw_connect(message, **kwargs)

    def receive(self, content, **kwargs):
        try:
            CallLog.objects.create(
                user=User.objects.get(username=self.message.user.username),
                type='message',
                action=self.message['path'],
                detail=self.message.content
            )
        except Exception as e:
            settings.logger.error(repr(e))
            try:
                settings.logger.error(self.message.user.username)
            except Exception as e:
                settings.logger.error(repr(e))
        settings.logger.info('recv_data:{data}'.format(data=content, path=self.message['path']))
        super(OmConsumer, self).receive(content, **kwargs)


class SaltConsumer(OmConsumer):
    def receive(self, content, **kwargs):
        super(SaltConsumer, self).receive(content, **kwargs)
        if not self.message.user.is_authenticated:
            self.send({'result': '未授权，请联系管理员！'})
            return
        if not self.message.user.is_superuser:
            self.send({'result': '仅管理员有权限执行该操作！'})
            return
        info = content.get('info', '')
        if info == 'refresh-server':
            update_from_salt(None if settings.OM_ENV == 'PRD' else 'UAT')
            self.send({'result': 'Y', 'info': 'refresh-server'})
        elif info == 'check_computer':
            self.send({'return': check_computer(), 'info': 'check_computer'})
        else:
            self.send({'result': '未知操作！'})


class ServerConsumer(OmConsumer):
    def receive(self, content, **kwargs):
        super(ServerConsumer, self).receive(content, **kwargs)
        if not self.message.user.is_authenticated:
            self.send({'result': '未授权，请联系管理员！'})
            return
        if not self.message.user.is_superuser:
            self.send({'result': '仅管理员有权限执行该操作！'})
            return
        if content.get('info', None) != 'syn_data_outside':
            self.send({'result': '未知操作！'})
            return
        syn_data_outside()
        self.send({'result': 'Y'})


class ActionDetailConsumer(OmConsumer):
    group_prefix = 'action_detail-'
    yes = {"result": 'Y'}
    no = {"result": 'N'}

    def label(self):
        reg = r'^/om/action_detail/(?P<task_id>[0-9]+)/$'
        task_id = re.search(reg, self.message['path']).group('task_id')
        return f'{self.group_prefix}{task_id}'

    def connection_groups(self, **kwargs):
        return self.groups or [self.label()]

    def receive(self, content, **kwargs):
        super(ActionDetailConsumer, self).receive(content, **kwargs)
        if not self.message.user.is_authenticated:
            self.send({'result': '未授权，请联系管理员！'})
            return
        self.group_send(self.label(), self.yes)

    @classmethod
    def task_change(cls, task_id):
        settings.logger.info(f'{cls.group_prefix}{task_id}')
        ActionDetailConsumer.group_send(f'{cls.group_prefix}{task_id}', cls.yes)


class UnlockWinConsumer(OmConsumer):
    def receive(self, content, **kwargs):
        super(UnlockWinConsumer, self).receive(content, **kwargs)
        if not self.message.user.is_authenticated:
            self.send({'result': '未授权，请联系管理员！'})
            return
        user = content.get('user', None)
        server_info = content.get('server_info', None)
        if not all([user, server_info]) or not all([user.strip(), server_info]):
            self.send({'result': '参数选择错误，请检查！'})

        agents = [x['name'] for x in server_info]

        if settings.OM_ENV == 'PRD':  # 只有生产环境可以双通
            prd_agents = list(SaltMinion.objects.filter(name__in=agents, env='PRD', os='Windows').values_list('name', flat=True))
            settings.logger.info('prd_agents:{ag}'.format(ag=repr(prd_agents)))
            uat_agents = list(SaltMinion.objects.exclude(env='PRD').filter(name__in=agents, os='Windows').values_list('name', flat=True))
            settings.logger.info('uat_agents:{ag}'.format(ag=repr(uat_agents)))
            if len(prd_agents) > 0:
                prd_result, prd_output = Salt('PRD').shell(prd_agents, f'net user {user} /active:yes')
            else:
                prd_result, prd_output = True, ''

            if len(uat_agents) > 0:
                uat_result, uat_output = Salt('UAT').shell(uat_agents, f'net user {user} /active:yes')
            else:
                uat_result, uat_output = True, ''

            salt_result = prd_result and uat_result
            salt_output = fmt_salt_out('{prd}\n{uat}'.format(prd=fmt_salt_out(prd_output), uat=fmt_salt_out(uat_output)))
        else:
            agents = list(SaltMinion.objects.exclude(env='PRD').filter(name__in=agents, os='Windows').values_list('name', flat=True))
            settings.logger.info('agents:{ag}'.format(ag=repr(agents)))
            if len(agents) > 0:
                salt_result, salt_output = Salt('UAT').shell(agents, 'net user {user} /active:yes'.format(user=user))
            else:
                salt_result, salt_output = True, ''
            salt_output = fmt_salt_out(salt_output)

        if salt_result:
            settings.logger.info('unlock success!')
            result = salt_output.replace('The command completed successfully', '解锁成功')
            result = result.replace('[{}]', '选中的机器不支持解锁，请联系基础架构同事解锁！')
            self.send({"result": result})
        else:
            settings.logger.info('unlock false for salt return false')
            self.send({"result": '解锁失败！'})


class CmdConsumer(OmConsumer):
    # noinspection PyBroadException
    def receive(self, content, **kwargs):
        super(CmdConsumer, self).receive(content, **kwargs)
        if not self.message.user.is_authenticated:
            self.send({'result': '未授权，请联系管理员！'})
            return
        name = content.get('name', '').strip()
        cmd = content.get('cmd', '').strip()
        user = content.get('user', '').strip()
        if not all([name, cmd, user]):
            self.send({'result': '参数错误！'})
            return
        try:
            pc = SaltMinion.objects.get(name=name, status='up')
            if not any(
                    [self.message.user.has_perm('om.can_exec_cmd'),
                     self.message.user.has_perm('om.can_exec_cmd', pc)]
            ):
                self.send({'result': '没有执行命令权限，请联系管理员！'})
                return
            if not any([self.message.user.has_perm('om.can_root'), self.message.user.has_perm('om.can_root', pc)]):
                if user == 'root':
                    self.send({'result': '没有root权限，请联系管理员！'})
                    return
            _, back = Salt(pc.env).shell(pc.name, cmd, None if user == 'NA' else user)
            self.send({'result': back['return'][0].get(name, '未知结果！')})
        except Exception as e:
            self.send({'result': f"{e}\n{content}"})


class MakeFireWallConsumer(OmConsumer):
    # noinspection PyBroadException
    def receive(self, content, **kwargs):
        super(MakeFireWallConsumer, self).receive(content, **kwargs)
        if not self.message.user.is_authenticated:
            self.send({'result': '未授权，请联系管理员！'})
            return
        s_ip = content.get('s_ip', '').strip()
        t_ip = content.get('t_ip', '').strip()
        port = content.get('port', '').strip()
        if not all([s_ip, t_ip, port]):
            self.send({'result': '参数错误！'})
            return
        s_ip = s_ip.replace('<pre>', '').replace('</pre>', '').split('<br>')
        t_ip = t_ip.replace('<pre>', '').replace('</pre>', '').split('<br>')
        port = port.replace('<pre>', '').replace('</pre>', '').split('<br>')
        try:
            src_ag = [SaltMinion.objects.get(name__endswith='-'+x) for x in s_ip]
            dst_ag = [SaltMinion.objects.get(name__endswith='-'+x) for x in t_ip]
            result = []
            for p in port:
                cf = CheckFireWall(src_ag, dst_ag, int(p))
                result.append(cf.check())
                # self.message.reply_channel.send({'text': json.dumps(result)}, immediately=True)
            self.send(result)
        except Exception as e:
            if self.message.user.is_superuser:
                self.send({'result': f"{e}\n{traceback.format_exc()}\n{content}"})
            else:
                self.send({'result': 'error'})


class CheckFireWallConsumer(OmConsumer):

    def check_port(self, src_list, dst_list, port):
        result = []
        for p in port:
            cf = CheckFireWall(src_list, dst_list, int(p))
            result.append(cf.check())
        self.send(result)

    def check_policy(self, src_list, dst_list, port):
        from utils.util import FireWallPolicy
        src = ';'.join([x.ip() for x in src_list])
        dst = ';'.join([x.ip() for x in dst_list])
        srv = ','.join([f'tcp/{x}' for x in port])
        self.send({
            'src': [x.ip() for x in src_list],
            'dst': [x.ip() for x in dst_list],
            'port': port,
            'protocol': 'TCP',
            'result': FireWallPolicy(src, dst, srv).check()
        })

    def receive(self, content, **kwargs):
        super(CheckFireWallConsumer, self).receive(content, **kwargs)
        if not self.message.user.is_authenticated:
            self.send({'result': '未授权，请联系管理员！'})
            return
        check_type = content.get('check_type', '')
        src = content.get('src', [])
        dst = content.get('dst', [])
        port = [int(x) for x in re.split(r'\W+', content.get('port', [''])[0]) if x.strip() != '']
        try:
            if all([src, dst, port]):
                src_list = [x for x in SaltMinion.objects.filter(pk__in=src)]
                dst_list = [x for x in SaltMinion.objects.filter(pk__in=dst)]
                if all([src_list, dst_list]):
                    if check_type == 'port':
                        self.check_port(src_list, dst_list, port)
                    elif check_type == 'policy':
                        self.check_policy(src_list, dst_list, port)
                    else:
                        self.send({'result': '类型错误'})
        except Exception as e:
            settings.logger.error(repr(e))
            if self.message.user.is_superuser:
                self.send({'result': f"{e}\n{traceback.format_exc()}\n{content}"})
            else:
                self.send({'result': '执行报错，请联系管理员检查！'})


om_routing = [
    SaltConsumer.as_route(path=r"^/om/salt_status/"),
    ActionDetailConsumer.as_route(path=r"^/om/action_detail/", attrs={'group_prefix': 'action_detail-'}),
    UnlockWinConsumer.as_route(path=r"^/om/unlock_win/"),
    CmdConsumer.as_route(path=r'^/om/admin_action/'),
    MakeFireWallConsumer.as_route(path=r'^/utils/make_firewall_table/'),
    CheckFireWallConsumer.as_route(path=r'^/utils/check_firewall/'),
    ServerConsumer.as_route(path=r'^/om/show_server/')
]
