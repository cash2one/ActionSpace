# coding=utf-8
from om import worker


channel_routing = [
    worker.SaltConsumer.as_route(path=r"^/om/salt_status/"),
    worker.ActionDetailConsumer.as_route(path=r"^/om/action_detail/", attrs={'group_prefix': 'action_detail-'}),
    worker.UnlockWinConsumer.as_route(path=r"/om/unlock_win/")
]
