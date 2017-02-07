# -*- encoding=utf-8 -*-
from django import template
from om.models import ExecUser
register = template.Library()


@register.filter(name='set_attr')
def set_attr(bound_field, attr_info):
    """
    :param bound_field:
    :param attr_info:形式为'key=value',多个参数使用逗号分隔
    :return:
    """
    info_list = [x.split('=') for x in attr_info.split(',')]
    for info in info_list:
        if len(info) == 2:
            bound_field.field.widget.attrs[info[0]] = info[1]
    return bound_field


@register.filter(name='only_superuser_has_root')
def only_superuser_has_root(bound_field, user):
    """
    :param bound_field:
    :param user:用户
    :return:
    """
    if not user.is_superuser:
        bound_field.field.widget.choices.queryset = ExecUser.objects.exclude(name='root')
    return bound_field
