# coding=utf-8
from __future__ import print_function
from channels import Group
from channels.auth import channel_session_user, channel_session_user_from_http
from ActionSpace import settings
from om.util import unlock_win, ActionDetail, update_salt_manage_status
from om.models import CallLog
from django.contrib.auth.models import User
import traceback
import re


def send_to_client(group, info):
    Group(group).send({"text": info})


def get_label(message, only_path=False):
    session = re.search(r'session_key=(?P<session_key>\w+)', message['query_string']).group('session_key')
    login_path = message['path'].replace('/', '-')
    if only_path:
        label = '{path}'.format(path=login_path)
    else:
        label = '{path}-{user}-{session}'.format(path=login_path, user=message.user.username, session=session)
    return label


@channel_session_user_from_http
def ws_connect(message):
    try:
        message.reply_channel.send({"accept": True})
        settings.logger.info('{user}, {path}, {query}'.format(
            user=message.user.username,
            path=message['path'],
            query=message['query_string']
        ))
        if message['path'].startswith('/om/action_detail/'):
            ActionDetail(message).connect()
    except Exception as e:
        settings.logger.error(repr(e))
        settings.logger.error(repr(traceback.format_exc()))


@channel_session_user
def ws_receive(message):
    try:
        settings.logger.info('{user}, {path}'.format(
            user=message.user.username,
            path=message['path']
        ))
        if message.user.is_authenticated:
            CallLog.objects.create(
                user=User.objects.get(username=message.user.username),
                type='message',
                action=message['path'],
                detail=message.content
            )
            if message['path'] == '/om/unlock_win/':
                unlock_win(message)
            elif message['path'].startswith('/om/action_detail/'):
                ad = ActionDetail(message)
                ad.send_change(ad.get_label())
            elif message['path'].startswith('/om/salt_status/'):
                if message.user.is_superuser:
                    update_salt_manage_status()
                    message.reply_channel.send({"text": 'Y'})
                else:
                    message.reply_channel.send({"text": '仅管理员有权限执行该操作！'})
        else:
            message.reply_channel.send({"text": '用户未授权'})
    except Exception as e:
        settings.logger.error(repr(e))
        settings.logger.error(repr(traceback.format_exc()))


@channel_session_user
def ws_disconnect(message):
    try:
        settings.logger.info('{user}, {path}'.format(
            user=message.user.username,
            path=message['path']
        ))
        if message['path'].startswith('/om/action_detail/'):
            ActionDetail(message).disconnect()
    except Exception as e:
        settings.logger.error(repr(e))
        settings.logger.error(repr(traceback.format_exc()))
