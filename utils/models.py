from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class Activity(models.Model):
    user = models.ForeignKey(User, verbose_name='姓名', default=None)
    guess = models.FloatField(verbose_name='值', default=1)
    voted = models.BooleanField(verbose_name='是否已投票', default=False)
    join = models.BooleanField(verbose_name='是否参加', default=True)

    def __str__(self):
        return self.name()

    def name(self):
        return self.user.last_name+self.user.first_name

    def vote(self, val):
        if self.voted:
            return False
        else:
            self.voted = True
            self.guess = float(val)
            self.join = True
            self.save()
            return True

    @staticmethod
    def init():
        Activity.objects.all().update(voted=False)

    class Meta:
        verbose_name = '活动'
        verbose_name_plural = '活动'
