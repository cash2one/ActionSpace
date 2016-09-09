# -*- encoding=utf-8 -*-
from django import template
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

