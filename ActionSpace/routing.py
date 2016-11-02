# coding=utf-8
from channels.routing import route
from om import worker


channel_routing = [
    route('websocket.connect', worker.ws_connect),
    route('websocket.receive', worker.ws_receive),
    route('websocket.disconnect', worker.ws_disconnect)
]
