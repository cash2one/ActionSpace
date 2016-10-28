# coding=utf-8
from __future__ import print_function
from channels import Group
from channels.sessions import channel_session
from random import randint


def send_to_client(group, info):
    Group(group).send({"text": info})


@channel_session
def ws_connect(message):
    print('ws_connect')
    Group('task', channel_layer=message.channel_layer).add(message.reply_channel)


@channel_session
def ws_receive(message):
    print('ws_receive')
    Group('task', channel_layer=message.channel_layer).send({
        "text": '%d:%s' % (randint(1, 100), message.content)})


@channel_session
def ws_disconnect(message):
    print('ws_disconnect')
    Group('task', channel_layer=message.channel_layer).discard(message.reply_channel)
