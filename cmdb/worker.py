# coding=utf-8
from django.utils import timezone
from om.worker import OmConsumer
from cmdb.util import update_computer


class ComputerUpdateConsumer(OmConsumer):
    def msg(self, msg):
        self.send({'result': msg})

    def receive(self, content, **kwargs):
        super(OmConsumer, self).receive(content, **kwargs)
        if not self.message.user.is_authenticated:
            self.msg('未授权，请联系管理员！')
            return
        if not self.message.user.is_superuser:
            self.msg('仅管理员有权限执行该操作！')
            return
        action_type = content.get('type', None)
        action_id = content.get('id', None)

        if not all([action_type, action_id]):
            self.msg('参数错误')
            return

        if action_type == 'computer':
            from om.util import cmdb_task
            cmdb_task.delay(timezone.now(), action_id, self)
            self.msg('任务已下发')
        else:
            self.msg('不支持的操作！')


cmdb_routing = [
    ComputerUpdateConsumer.as_route(path=r"^/cmdb/$"),
]
