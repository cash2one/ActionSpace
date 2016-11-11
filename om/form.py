# coding=utf-8
from django import forms
from django.utils.encoding import force_text
from django.utils.html import format_html
from om.models import Job, JobGroup, Computer, Flow, TaskJob
from ActionSpace.settings import OM_ENV


# from itertools import chain


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
    # def __init__(self, *args, **kwargs):
    #     super(JobForm, self).__init__(*args, **kwargs)
    #     env_list = ['PRD', 'UAT', 'FAT']
    #     server_list_choices = [(e, [(c.ip, '%s-%s' % (c.host, c.ip)) for c in Computer.objects.filter(env=e)]) for e in env_list]
    #     self.fields['server_list'].choices = server_list_choices

    server_list = forms.ModelMultipleChoiceField(
        queryset=Computer.objects.filter(env=OM_ENV).order_by('ip'),
        # widget=forms.CheckboxSelectMultiple,
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
        #  widgets = {
        #      'script_content#  ': forms.Textarea(),  # 修改表单控件为文本域
        #  }


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
            'pause_when_finish', 'pause_finish_tip', 'exec_output'
        )
