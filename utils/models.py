from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Activity(models.Model):
    user = models.ForeignKey(User, verbose_name='姓名', default=None)
    guess = models.FloatField(verbose_name='值', default=1)
    voted = models.BooleanField(verbose_name='是否已投票', default=False)
    join = models.BooleanField(verbose_name='是否参加', default=True)
    last_update = models.DateTimeField(verbose_name='最后更新时间', default=timezone.now)

    def __str__(self):
        return self.name()

    def name(self):
        return self.user.last_name+self.user.first_name

    def vote(self, val):
        if self.voted:
            return False
        else:
            self.voted = True
            self.last_update = timezone.now()
            self.guess = float(val)
            self.join = True
            self.save()
            return True

    @staticmethod
    def init():
        Activity.objects.all().update(voted=False, last_update=timezone.now())

    class Meta:
        verbose_name = '活动'
        verbose_name_plural = '活动'


class CommonAddress(models.Model):
    name = models.CharField(max_length=50, verbose_name='名称', default='')
    desc = models.CharField(max_length=255, verbose_name='说明', default='', blank=True)
    url = models.URLField(verbose_name='URL地址', default='')
    icon_url = models.URLField(verbose_name='图标URL地址', default='', blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '常用地址'
        verbose_name_plural = '常用地址'


class NetArea(models.Model):
    name = models.CharField(max_length=50, verbose_name='网络区域')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '网络区域'
        verbose_name_plural = '网络区域'


class NetRegion(models.Model):
    name = models.CharField(max_length=50, verbose_name='网段')
    area = models.ForeignKey(NetArea, verbose_name='网络区域', blank=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '网段'
        verbose_name_plural = '网段'


class NetInfo(models.Model):
    ip = models.GenericIPAddressField(verbose_name='IP')
    mask = models.GenericIPAddressField(verbose_name='掩码', default='255.255.255.0')
    region = models.ForeignKey(NetRegion, verbose_name='网段', blank=False)

    def __str__(self):
        return f'{self.ip}/{self.mask}'

    class Meta:
        verbose_name = 'IP段'
        verbose_name_plural = 'IP段'
        ordering = ['ip']
