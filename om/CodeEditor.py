# coding=utf-8
from codemirror import CodeMirrorTextarea
from django.utils.safestring import mark_safe


class CodeEditor(CodeMirrorTextarea):
    def __init__(self, related_id=None, related_map=None, attrs=None, mode=None, theme=None, config=None, dependencies=(),
                 js_var_format=None, addon_js=(), addon_css=(), custom_mode=None, custom_js=(),
                 keymap=None, custom_css=None, **kwargs):
        super(CodeEditor, self).__init__(
            attrs, mode, theme, config, dependencies, js_var_format, addon_js, addon_css,
            custom_mode, custom_js, keymap, custom_css, **kwargs)
        self.related_id = related_id
        self.related_map = {'PY': 'python', 'SHELL': 'shell', 'BAT': 'perl'} if related_map is None else related_map

    def render(self, name, value, attrs=None):
        before = []
        after = []
        if self.related_id is not None:
            lang_js = '<script type="text/javascript" src="/static/codemirror/mode/{lang}/{lang}.js" ></script>'
            [before.append(lang_js.format(lang=x)) for x in self.related_map.values()]
            before.append('<script src = "//cdn.bootcss.com/jquery/3.1.0/jquery.min.js" ></script>')
            code_map = ''
            for k, v in self.related_map.items():
                code_map += '''
            case '{k}':
                {n}_editor.setOption("mode", "{v}");
                break;'''.format(n=name, k=k, v=v)
            after.append('''
    <script type="text/javascript">
        function set_code_for_{name}(val) {
            switch (val) {{code_map}
            };
        }
        set_code_for_{name}($('#{related_id}').val())
        $('#{related_id}').change(function(){
            var script_type = $(this).children('option:selected').val();
            set_code_for_{name}(script_type);
        });
    </script>
            '''.replace('{related_id}', self.related_id).replace('{code_map}', code_map).replace('{name}', name))
        output = ['\n'.join(before), super(CodeEditor, self).render(name, value, attrs), '\n'.join(after)]
        return mark_safe('\n'.join(output))
