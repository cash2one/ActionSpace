# coding=utf-8
import re
from django import forms
from django_select2.forms import ModelSelect2MultipleWidget
from om.models import Entity, SaltMinion


def check_port(v):
    if not all([x.isdecimal() for x in re.split(r'\W+', v)]):
        raise forms.ValidationError('填写非法，多个端口可用空格或逗号分隔！', params={'value': v}, )


class CheckWallForm(forms.Form):
    src = forms.ModelMultipleChoiceField(
        widget=ModelSelect2MultipleWidget(queryset=SaltMinion.objects.filter(status='up'), search_fields=['name__icontains']),
        queryset=SaltMinion.objects.filter(status='up'), label='源'
    )

    dst = forms.ModelMultipleChoiceField(
        widget=ModelSelect2MultipleWidget(queryset=SaltMinion.objects.filter(status='up'), search_fields=['name__icontains']),
        queryset=SaltMinion.objects.filter(status='up'), label='目标'
    )

    port = forms.CharField(
        min_length=1, max_length=200, label='端口',
        validators=[check_port],
        error_messages={'required': '请填写监听端口，多个端口可用空格或逗号分隔！'},
        widget=forms.TextInput(attrs={'placeholder': '多个端口可用空格或逗号分隔！'})
    )

    def clean(self):
        if not self.is_valid():
            raise forms.ValidationError(u"所有项都为必填项！")
        else:
            cleaned_data = super(CheckWallForm, self).clean()
        return cleaned_data


class WallForm(forms.Form):
    source_entity = forms.ModelMultipleChoiceField(
        widget=ModelSelect2MultipleWidget(model=Entity, search_fields=['name__icontains']),
        queryset=Entity.objects.all(), label='请求方实体'
    )

    target_entity = forms.ModelMultipleChoiceField(
        widget=ModelSelect2MultipleWidget(model=Entity, search_fields=['name__icontains']),
        queryset=Entity.objects.all(), label='响应方实体'
    )

    port = forms.CharField(
        min_length=1, max_length=200, label='服务端口',
        validators=[check_port],
        error_messages={'required': '请填写监听端口，多个端口可用空格或逗号分隔！'},
        widget=forms.TextInput(attrs={'placeholder': '多个端口可用空格或逗号分隔！'})
    )

    env = forms.ChoiceField(choices=(('PRD', '生产'), ('UAT', '测试'), ('FAT', '开发')), label='环境类型')

    # om = forms.ChoiceField(choices=(('t', '生成'), ('n', '不生成')), label='运维防火墙')

    def clean(self):
        if not self.is_valid():
            raise forms.ValidationError(u"所有项都为必填项！")
        else:
            cleaned_data = super(WallForm, self).clean()
        return cleaned_data
