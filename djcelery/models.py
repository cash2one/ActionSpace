from __future__ import absolute_import, unicode_literals

from datetime import timedelta
from time import time, mktime, gmtime

from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.db import models
from django.db.models import signals
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from celery import schedules
from celery import states
from celery.events.state import heartbeat_expires

from . import managers
from .picklefield import PickledObjectField
from .utils import now
from .compat import python_2_unicode_compatible

ALL_STATES = sorted(states.ALL_STATES)
TASK_STATE_CHOICES = sorted(zip(ALL_STATES, ALL_STATES))


def cronexp(field):
    return field and str(field).replace(' ', '') or '*'


@python_2_unicode_compatible
class TaskMeta(models.Model):
    """Task result/status."""
    task_id = models.CharField(verbose_name='任务ID', max_length=255, unique=True)
    status = models.CharField(
        verbose_name='任务状态',
        max_length=50, default=states.PENDING, choices=TASK_STATE_CHOICES,
    )
    result = PickledObjectField(null=True, default=None, editable=False)
    date_done = models.DateTimeField(_('done at'), auto_now=True)
    traceback = models.TextField(_('traceback'), blank=True, null=True)
    hidden = models.BooleanField(editable=False, default=False, db_index=True)
    # TODO compression was enabled by mistake, we need to disable it
    # but this is a backwards incompatible change that needs planning.
    meta = PickledObjectField(
        compress=True, null=True, default=None, editable=False,
    )

    objects = managers.TaskManager()

    class Meta:
        verbose_name = '任务状态'
        verbose_name_plural = '任务状态'
        db_table = 'celery_taskmeta'

    def to_dict(self):
        return {'task_id': self.task_id,
                'status': self.status,
                'result': self.result,
                'date_done': self.date_done,
                'traceback': self.traceback,
                'children': (self.meta or {}).get('children')}

    def __str__(self):
        return '<Task: {0.task_id} state={0.status}>'.format(self)


@python_2_unicode_compatible
class TaskSetMeta(models.Model):
    """TaskSet result"""
    taskset_id = models.CharField(_('group id'), max_length=255, unique=True)
    result = PickledObjectField()
    date_done = models.DateTimeField(_('created at'), auto_now=True)
    hidden = models.BooleanField(editable=False, default=False, db_index=True)

    objects = managers.TaskSetManager()

    class Meta:
        """Model meta-data."""
        verbose_name = _('saved group result')
        verbose_name_plural = _('saved group results')
        db_table = 'celery_tasksetmeta'

    def to_dict(self):
        return {'taskset_id': self.taskset_id,
                'result': self.result,
                'date_done': self.date_done}

    def __str__(self):
        return '<TaskSet: {0.taskset_id}>'.format(self)


PERIOD_CHOICES = (('days', '天'),
                  ('hours', '小时'),
                  ('minutes', '分钟'),
                  ('seconds', '秒'),
                  ('microseconds', '毫秒'))


@python_2_unicode_compatible
class IntervalSchedule(models.Model):
    every = models.IntegerField(verbose_name='周期数', null=False)
    period = models.CharField(
        verbose_name='周期单位', max_length=24, choices=PERIOD_CHOICES,
    )

    class Meta:
        verbose_name = '周期控制器'
        verbose_name_plural = '周期控制器'
        ordering = ['period', 'every']

    @property
    def schedule(self):
        return schedules.schedule(timedelta(**{self.period: self.every}))

    @classmethod
    def from_schedule(cls, schedule, period='seconds'):
        every = max(schedule.run_every.total_seconds(), 0)
        try:
            return cls.objects.get(every=every, period=period)
        except cls.DoesNotExist:
            return cls(every=every, period=period)
        except MultipleObjectsReturned:
            cls.objects.filter(every=every, period=period).delete()
            return cls(every=every, period=period)

    def __str__(self):
        if self.every == 1:
            return 'every {0.period_singular}'.format(self)
        return 'every {0.every:d} {0.period}'.format(self)

    @property
    def period_singular(self):
        return self.period[:-1]


@python_2_unicode_compatible
class CrontabSchedule(models.Model):
    minute = models.CharField(verbose_name='分（minute）', max_length=64, default='*')
    hour = models.CharField(verbose_name='时（hour）', max_length=64, default='*')
    day_of_month = models.CharField(
        verbose_name='日（day of month）', max_length=64, default='*',
    )
    month_of_year = models.CharField(
        verbose_name='月（month of year）', max_length=64, default='*',
    )
    day_of_week = models.CharField(
        verbose_name='周（day of week）', max_length=64, default='*',
    )

    class Meta:
        verbose_name = '定时控制器'
        verbose_name_plural = '定时控制器'
        ordering = ['month_of_year', 'day_of_month',
                    'day_of_week', 'hour', 'minute']

    def __str__(self):
        return '{0} {1} {2} {3} {4} (m/h/dM/MY/d/)'.format(
            cronexp(self.minute),
            cronexp(self.hour),
            cronexp(self.day_of_month),
            cronexp(self.month_of_year),
            cronexp(self.day_of_week),
        )

    @property
    def schedule(self):
        return schedules.crontab(minute=self.minute,
                                 hour=self.hour,
                                 day_of_month=self.day_of_month,
                                 month_of_year=self.month_of_year,
                                 day_of_week=self.day_of_week)

    # noinspection PyProtectedMember
    @classmethod
    def from_schedule(cls, schedule):
        spec = {
            'minute': schedule._orig_minute,
            'hour': schedule._orig_hour,
            'day_of_month': schedule._orig_day_of_month,
            'month_of_year': schedule._orig_month_of_year,
            'day_of_week': schedule._orig_day_of_week
        }
        try:
            return cls.objects.get(**spec)
        except cls.DoesNotExist:
            return cls(**spec)
        except MultipleObjectsReturned:
            cls.objects.filter(**spec).delete()
            return cls(**spec)


class PeriodicTasks(models.Model):
    ident = models.SmallIntegerField(default=1, primary_key=True, unique=True)
    last_update = models.DateTimeField(null=False)

    objects = managers.ExtendedManager()

    # noinspection PyUnusedLocal
    @classmethod
    def changed(cls, instance, **kwargs):
        if not instance.no_changes:
            cls.objects.update_or_create(ident=1,
                                         defaults={'last_update': now()})

    @classmethod
    def last_change(cls):
        try:
            return cls.objects.get(ident=1).last_update
        except cls.DoesNotExist:
            pass


@python_2_unicode_compatible
class PeriodicTask(models.Model):
    name = models.CharField(
        verbose_name='任务名', max_length=200, unique=True,
        help_text=_('使用说明'),
    )
    task = models.CharField(verbose_name='任务名', max_length=200)
    interval = models.ForeignKey(
        IntervalSchedule,
        null=True, blank=True, verbose_name='周期控制器',
        on_delete=models.CASCADE,
    )
    crontab = models.ForeignKey(
        CrontabSchedule, null=True, blank=True, verbose_name='定时控制器',
        on_delete=models.CASCADE,
        help_text=_('选择定时控制器或者周期控制器之一'),
    )
    args = models.TextField(
        verbose_name='参数列表', blank=True, default='[]',
        help_text=_('JSON编码的位置参数'),
    )
    kwargs = models.TextField(
        verbose_name='参数字典', blank=True, default='{}',
        help_text=_('JSON编码的关键字参数'),
    )
    queue = models.CharField(
        verbose_name='队列', max_length=200, blank=True, null=True, default=None,
        help_text=_('默认使用CELERY_QUEUES定义的队列'),
    )
    exchange = models.CharField(
        verbose_name='交换', max_length=200, blank=True, null=True, default=None,
    )
    routing_key = models.CharField(
        '路由关键字', max_length=200, blank=True, null=True, default=None,
    )
    expires = models.DateTimeField(
        '失效时间', blank=True, null=True,
    )
    enabled = models.BooleanField(
        verbose_name='启用', default=True,
    )
    last_run_at = models.DateTimeField(
        auto_now=False, auto_now_add=False,
        editable=False, blank=True, null=True,
    )
    total_run_count = models.PositiveIntegerField(
        default=0, editable=False,
    )
    date_changed = models.DateTimeField(auto_now=True)
    description = models.TextField(_('description'), blank=True)

    founder = models.CharField(max_length=50, verbose_name='创建人', default='NA')
    locked = models.BooleanField(verbose_name='锁定', default=False)
    last_modified_by = models.CharField(max_length=50, verbose_name='最后修改人', default='NA')
    created_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    last_modified_time = models.DateTimeField(verbose_name='最后修改时间', auto_now=True)

    objects = managers.PeriodicTaskManager()
    no_changes = False

    class Meta:
        verbose_name = '任务管理'
        verbose_name_plural = '任务管理'

    def validate_unique(self, *args, **kwargs):
        super(PeriodicTask, self).validate_unique(*args, **kwargs)
        if not self.interval and not self.crontab:
            raise ValidationError(
                {'interval': ['至少选择一种控制器。']})
        if self.interval and self.crontab:
            raise ValidationError(
                {'crontab': ['只能选择一种控制器。']})

    def save(self, *args, **kwargs):
        self.exchange = self.exchange or None
        self.routing_key = self.routing_key or None
        self.queue = self.queue or None
        if not self.enabled:
            self.last_run_at = None
        super(PeriodicTask, self).save(*args, **kwargs)

    def __str__(self):
        fmt = '{0.name}: {{no schedule}}'
        if self.interval:
            fmt = '{0.name}: {0.interval}'
        if self.crontab:
            fmt = '{0.name}: {0.crontab}'
        return fmt.format(self)

    @property
    def schedule(self):
        if self.interval:
            return self.interval.schedule
        if self.crontab:
            return self.crontab.schedule

signals.pre_delete.connect(PeriodicTasks.changed, sender=PeriodicTask)
signals.pre_save.connect(PeriodicTasks.changed, sender=PeriodicTask)


class WorkerState(models.Model):
    hostname = models.CharField(_('hostname'), max_length=255, unique=True)
    last_heartbeat = models.DateTimeField(_('last heartbeat'), null=True,
                                          db_index=True)

    objects = managers.ExtendedManager()

    class Meta:
        """Model meta-data."""
        verbose_name = _('worker')
        verbose_name_plural = _('workers')
        get_latest_by = 'last_heartbeat'
        ordering = ['-last_heartbeat']

    def __str__(self):
        return self.hostname

    def __repr__(self):
        return '<WorkerState: {0.hostname}>'.format(self)

    def is_alive(self):
        if self.last_heartbeat:
            # Use UTC timestamp if USE_TZ is true, or else use local timestamp
            timestamp = mktime(gmtime()) if settings.USE_TZ else time()
            return timestamp < heartbeat_expires(self.heartbeat_timestamp)
        return False

    @property
    def heartbeat_timestamp(self):
        return mktime(self.last_heartbeat.timetuple())


@python_2_unicode_compatible
class TaskState(models.Model):
    state = models.CharField(
        _('state'), max_length=64, choices=TASK_STATE_CHOICES, db_index=True,
    )
    task_id = models.CharField(_('UUID'), max_length=36, unique=True)
    name = models.CharField(
        _('name'), max_length=200, null=True, db_index=True,
    )
    tstamp = models.DateTimeField(_('event received at'), db_index=True)
    args = models.TextField(_('Arguments'), null=True)
    kwargs = models.TextField(_('Keyword arguments'), null=True)
    eta = models.DateTimeField(_('ETA'), null=True)
    expires = models.DateTimeField(_('expires'), null=True)
    result = models.TextField(_('result'), null=True)
    traceback = models.TextField(_('traceback'), null=True)
    runtime = models.FloatField(
        _('execution time'), null=True,
        help_text=_('in seconds if task succeeded'),
    )
    retries = models.IntegerField(_('number of retries'), default=0)
    worker = models.ForeignKey(
        WorkerState, null=True, verbose_name=_('worker'),
        on_delete=models.CASCADE,
    )
    hidden = models.BooleanField(editable=False, default=False, db_index=True)

    objects = managers.TaskStateManager()

    class Meta:
        """Model meta-data."""
        verbose_name = _('task')
        verbose_name_plural = _('tasks')
        get_latest_by = 'tstamp'
        ordering = ['-tstamp']

    def __str__(self):
        name = self.name or 'UNKNOWN'
        s = '{0.state:<10} {0.task_id:<36} {1}'.format(self, name)
        if self.eta:
            s += ' eta:{0.eta}'.format(self)
        return s

    def __repr__(self):
        return '<TaskState: {0.state} {1}[{0.task_id}] ts:{0.tstamp}>'.format(
            self, self.name or 'UNKNOWN',
        )
