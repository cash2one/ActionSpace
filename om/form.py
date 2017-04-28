# coding=utf-8
from django import forms
from django.contrib.auth.models import User
from django.utils.encoding import force_text
from django.utils.html import format_html
from om.models import Job, JobGroup, Computer, Flow, TaskJob, MailGroup
from django_select2.forms import ModelSelect2MultipleWidget
from ActionSpace.settings import OM_ENV


class OrderedMultiSelect(forms.SelectMultiple):
    """
    多选组件，能保持已选中的顺序，并且把已选中的置于最前端，剩下的放在最后
    """

    def render_options(self, selected_choices):
        output = []
        new_choices_info = []
        int_selected = []
        if selected_choices:
            int_selected = [int(x) for x in selected_choices.split(',') if x.isdigit()]

        # 将已选中的提前并保持顺序
        [[new_choices_info.append(c) for c in self.choices if s == c[0]] for s in int_selected]

        # 剩下没选的放到后面
        [new_choices_info.append(c) for c in self.choices if c[0] not in int_selected]

        new_selected = []
        if not isinstance(selected_choices, list):
            # 将选中项变为list，避免出现3 in 33为True的情况
            new_selected = [x for x in selected_choices.split(',')]

        # for option_value, option_label in chain(self.choices, new_choices_info):
        for option_value, option_label in new_choices_info:
            if isinstance(option_label, (list, tuple)):
                output.append(format_html('<optgroup label="{}">', force_text(option_value)))
                for option in option_label:
                    output.append(self.render_option(new_selected, *option))
                output.append('</optgroup>')
            else:
                output.append(self.render_option(new_selected, option_value, option_label))
        return '\n'.join(output)


class JobForm(forms.ModelForm):
    #  def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
    #               initial=None, error_class=ErrorList, label_suffix=None,
    #               empty_permitted=False, instance=None, use_required_attribute=None):
    #      from django.forms import model_to_dict, BaseModelForm
    #      from django.forms.utils import ErrorList
    #      from om.models import ComputerGroup
    #      opts = self._meta
    #      if opts.model is None:
    #          raise ValueError('ModelForm has no model class specified.')
    #      if instance is None:
    #          self.instance = opts.model()
    #          object_data = {}
    #      else:
    #          self.instance = instance
    #          object_data = model_to_dict(instance, opts.fields, opts.exclude)
    #      if initial is not None:
    #          object_data.update(initial)
    #      self._validate_unique = False
    #  
    #      # diy begin
    #      if instance is not None:
    #          server_list = set(list(instance.server_list.values_list('id', flat=True)))
    #          cg_list = []
    #          for cg in ComputerGroup.objects.all():
    #              cg_cp_list = set(list(cg.computer_list.values_list('id', flat=True)))
    #              if server_list.issuperset(cg_cp_list):
    #                  cg_list.append(cg.id)
    #          object_data['server_group_list'] = ComputerGroup.objects.filter(id__in=cg_list)
    #      # diy end
    #  
    #      self._validate_unique = False
    #      super(BaseModelForm, self).__init__(
    #          data, files, auto_id, prefix, object_data, error_class,
    #          label_suffix, empty_permitted, use_required_attribute=use_required_attribute,
    #      )
    #  
    #      for field_name in self.fields:
    #          formfield = self.fields[field_name]
    #          if hasattr(formfield, 'queryset') and hasattr(formfield, 'get_limit_choices_to'):
    #              limit_choices_to = formfield.get_limit_choices_to()
    #              if limit_choices_to is not None:
    #                  formfield.queryset = formfield.queryset.complex_filter(limit_choices_to)
    #  
    #  server_group_list = forms.ModelMultipleChoiceField(
    #      queryset=ComputerGroup.objects.all(),
    #      required=False, label='服务器组（列表）'
    #  )

    server_list = forms.ModelMultipleChoiceField(
        widget=ModelSelect2MultipleWidget(
            queryset=Computer.objects.filter(env=OM_ENV) if OM_ENV == 'UAT' else Computer.objects.all(),
            search_fields=[
                'agent_name__icontains',
                'ip__icontains',
                'host__icontains'
            ],
            data_view='om:ComputerTaskView'
        ),
        queryset=Computer.objects.filter(env=OM_ENV) if OM_ENV == 'UAT' else Computer.objects.all(),
        required=False, label='服务器（列表）'
    )

    def save_form(self, request, commit=True, create=False):
        self.instance.last_modified_by = request.user.username
        if not hasattr(self, 'cleaned_data'):
            super(JobForm, self).save()
        if not create:
            self.instance.founder = request.user.username
        return super(JobForm, self).save(commit)

    class Meta:
        model = Job
        fields = '__all__'
        exclude = ('last_modified_by', 'founder')


class JobGroupForm(forms.ModelForm):
    job_list_comma_sep = forms.CharField(required=False, label=u'已选择作业列表')
    job_list = forms.ModelMultipleChoiceField(
        queryset=Job.objects.all(),
        widget=OrderedMultiSelect,
        required=False,
        label=u'作业列表'
    )

    def save_form(self, request, commit=True, create=False):
        self.instance.last_modified_by = request.user.username
        self.instance.job_list = request.POST['job_list_comma_sep']
        if create:
            self.instance.founder = request.user.username
        return super(JobGroupForm, self).save(commit)

    class Meta:
        model = JobGroup
        fields = '__all__'
        exclude = ('last_modified_by', 'founder')


class FlowForm(forms.ModelForm):
    class Meta:
        model = Flow
        fields = '__all__'
        exclude = ('last_modified_by', 'founder', 'job_group_list', 'is_quick_flow')


class TaskItemForm(forms.ModelForm):
    class Meta:
        model = TaskJob
        fields = '__all__'
        exclude = (
            'job_id', 'group', 'status', 'pause_need_confirm',
            'pause_when_finish', 'pause_finish_tip', 'exec_output', 'step'
        )


class ChgPwdForm(forms.Form):
    old_pwd = forms.CharField(
        required=True,
        label=u"原密码",
        error_messages={'required': u'请输入原密码'},
        widget=forms.PasswordInput(
            attrs={
                'placeholder': u"原密码",
            }
        ),
    )
    new_pwd = forms.CharField(
        required=True,
        label=u"新密码",
        error_messages={'required': u'请输入新密码'},
        widget=forms.PasswordInput(
            attrs={
                'placeholder': u"新密码",
            }
        ),
    )
    new_pwd_confirm = forms.CharField(
        required=True,
        label=u"确认密码",
        error_messages={'required': u'请再次输入新密码'},
        widget=forms.PasswordInput(
            attrs={
                'placeholder': u"确认密码",
            }
        ),
    )

    def clean(self):
        if not self.is_valid():
            raise forms.ValidationError(u"所有项都为必填项")
        elif self.cleaned_data['new_pwd'] != self.cleaned_data['new_pwd_confirm']:
            raise forms.ValidationError(u"两次输入的新密码不一样")
        else:
            cleaned_data = super(ChgPwdForm, self).clean()
        return cleaned_data


class MailGroupForm(forms.ModelForm):
    user_list = forms.ModelMultipleChoiceField(
        required=True, label='用户列表', queryset=User.objects.exclude(email='')
    )

    class Meta:
        model = MailGroup
        fields = '__all__'
        exclude = ('job_id', 'last_modified_by')
