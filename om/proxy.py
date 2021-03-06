# coding=utf-8
from base64 import b85decode as pw
from ActionSpace.settings import logger
from pprint import pformat
import requests
import uuid


class Salt(object):
    """
    以下内容摘自salt官网（https://docs.saltstack.com/en/latest/ref/clients/index.html#salt.client.LocalClient.cmd_batch）：
    tgt (string or list) --
        Which minions to target for the execution. Default is shell glob. Modified by the expr_form option.
    fun (string or list of strings) --
        The module and function to call on the specified minions of the form module.function. For example test.ping or grains.items.
        Compound commands
            Multiple functions may be called in a single publish by passing a list of commands. This can dramatically lower overhead and speed up the application communicating with Salt.
            This requires that the arg param is a list of lists. The fun list and the arg list must correlate by index meaning a function that does not take arguments must still have a corresponding empty list at the expected index.
    arg (list or list-of-lists) --
        A list of arguments to pass to the remote function. If the function takes no arguments arg may be omitted except when executing a compound command.
    timeout --
        Seconds to wait after the last minion returns but before all minions return.
    expr_form --
        The type of tgt. Allowed values:
        glob -
            Bash glob completion - Default
        pcre -
            Perl style regular expression，E -- 针对 minion 针对正则表达式做匹配，例如：E@web\d+.(dev|qa|prod).loc
        list -
            Python list of hosts，L -- 针对 minion 做列表匹配，例如：L@minion1.example.com,minion3.domain.com or bl*.domain.com
        grain -
            Match based on a grain comparison，G -- 针对 Grains 做单个匹配，例如：G@os:Ubuntu
        grain_pcre -
            Grain comparison with a regex
        pillar -
            Pillar data comparison，I -- 针对 Pillar 做单个匹配，例如：I@pdata:foobar
        pillar_pcre -
            Pillar data comparison with a regex
        nodegroup -
            Match on nodegroup，N,--nodegroup，例如：'L@SN2013-08-22,SN2014'
        range -
            Use a Range server for matching，R -- 针对客户端范围做匹配，例如： R@%foo.bar
        compound -
            Pass a compound match string，-C,--compound,根据条件运算符not、and、or去匹配不同规则的主机信息，例如：'E@^SN2013.* and G@os:Centos'
    """

    SALT_INFO = {
        'UAT': {'url': 'salturl', 'user': 'saltuser', 'pwd': 'saltpwd_pw'},
        'PRD': {'url': 'salturl', 'user': 'saltuser', 'pwd': 'saltpwd_pw'}
    }

    FILE_SERVER = 'fileserverurl'

    # noinspection PyUnresolvedReferences
    def __init__(self, env):
        if env not in ['UAT', 'PRD']:
            raise Exception('env type should in [UAT, PRD] but {env}'.format(env=env))
        self.login_info = self.SALT_INFO[env]
        self.url = self.login_info['url']
        requests.packages.urllib3.disable_warnings()
        result = requests.post(url=self.url+'/login', verify=False, data={
            'username': self.login_info['user'], 'password': pw(self.login_info['pwd']).decode(), 'eauth': 'pam'
        })
        self.default_host_type = 'compound'
        self.client_type = 'local'
        assert result.status_code == 200, result.text
        self.token = result.cookies

    def _post(self, hosts, data):
        if hosts is not None:
            host_multi = isinstance(hosts, (list, set)) and len(hosts) > 1
            if data.get('expr_form') is None:
                data['expr_form'] = 'list' if host_multi else self.default_host_type
            if data.get('client') is None:
                data['client'] = self.client_type
            data['tgt'] = ','.join(hosts) if host_multi else hosts
        logger.info('data:{data}'.format(data=str(data)))
        back = requests.post(url=self.url, cookies=self.token, verify=False, data=data)
        result = back.json() if back.status_code == 200 else back.text
        return back.status_code == 200, result

    def file_trans(self, hosts, file_name, target_name):
        result, back = self._post(hosts, {'fun': 'cp.get_url', 'arg': [
            self.FILE_SERVER + file_name, target_name
        ]})
        logger.info('{r}:{b}'.format(r=result, b=pformat(back)))
        return result, back

    def shell(self, hosts, cmd, user=None):
        if user is not None:
            result, back = self._post(hosts, {'fun': 'cmd.run', 'arg': [cmd, 'runas={user}'.format(user=user)]})
        else:
            result, back = self._post(hosts, {'fun': 'cmd.run', 'arg': cmd})
        logger.info('{r}:{b}'.format(r=result, b=pformat(back)))
        return result, back

    def python(self, hosts, cmd):
        result, back = self._post(hosts, {'fun': 'cmd.exec_code_all', 'arg': ['python', cmd]})
        logger.info('{r}:{b}'.format(r=result, b=pformat(back)))
        return result, back

    def ping(self, hosts):
        result, back = self._post(hosts, {'fun': 'test.ping'})
        logger.info('{r}:{b}'.format(r=result, b=pformat(back)))
        return result, back

    def manage_status(self):
        result, back = self._post(None, {'client': 'runner', 'fun': 'manage.status'})
        logger.info('{r}:{b}'.format(r=result, b='long ...'))
        return result, back

    def grains(self, host, items=None):
        arg = {'fun': 'grains.items'} if items is None else {'fun': 'grains.item', 'arg': items}
        result, back = self._post(host, arg)
        logger.info('{r}:{b}'.format(r=result, b=repr(items)))
        return result, back

    def os_type(self, host='*'):
        return self.grains(host, ['os'])

    def hwaddr_interfaces(self, host='*'):
        return self.grains(host, ['hwaddr_interfaces'])

    def linux_shell(self, agents, script, param, user, delete_after_exec=True):
        cmd = script
        dos2unix = cmd.replace('\r\n', '\n').replace("'", r"'\''")
        default_shell = '' if cmd.startswith('#!') else "#!/bin/bash\n"
        tmp_file = f'/tmp/{uuid.uuid4()}.sh'
        cmd = f'''echo '{default_shell}{dos2unix}
        '>"{tmp_file}";chmod u+x "{tmp_file}";"{tmp_file}"'''
        if param.strip() != '':
            cmd += f' {param.strip()}'
        if delete_after_exec:
            cmd += f';[ -f "{tmp_file}" ] && rm -f "{tmp_file}"'
        return self.shell(agents, cmd, user)

    def windows_batch(self, agents, script, param, delete_after_exec=True):
        escaped_list = r'\()&|%<>'
        tmp_file = f'%tmp%\\{uuid.uuid4()}.bat'
        cmd = 'echo off&('
        for line in script.split('\n'):
            last_line = line.strip()
            if last_line != '':
                for ec in escaped_list:
                    last_line = last_line.replace(ec, f'^{ec}')
                cmd += f'echo {last_line}&'
        cmd += f'echo.)>"{tmp_file}"&"{tmp_file}"'
        if delete_after_exec:
            cmd += f'&del "{tmp_file}"'
        cmd += '&echo on'
        if param.strip() != '':
            cmd += f' {param.strip()}'
        return self.shell(agents, cmd)
