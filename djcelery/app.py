from __future__ import absolute_import, unicode_literals
from django.apps import AppConfig
from celery import current_app


#: The Django-Celery app instance.
# noinspection PyProtectedMember
app = current_app._get_current_object()


class CeleryConfig(AppConfig):
    name = 'djcelery'
    verbose_name = '自动任务'
