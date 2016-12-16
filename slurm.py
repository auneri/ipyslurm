from __future__ import absolute_import, division, print_function

import sys
import time
from getpass import getpass

import paramiko
from IPython.core import magic
from IPython.display import clear_output
from six import print_ as print
from six.moves import input


@magic.magics_class
class Slurm(magic.Magics):

    def __init__(self, *args, **kwargs):
        super(Slurm, self).__init__(*args, **kwargs)
        self._ssh = None

    def __del__(self):
        self.logout()
        super(Slurm, self).__del__()

    def loggedin(self):
        if self._ssh is None:
            print('Please login to cluster using %slogin', file=sys.stderr)
        return self._ssh is not None

    def login(self, server, username, password):
        try:
            self._ssh = paramiko.SSHClient()
            self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._ssh.connect(server, username=username, password=password)
        except paramiko.AuthenticationException:
            self.logout()
            raise

    def logout(self):
        if self._ssh is not None:
            self._ssh.close()
            self._ssh = None

    @magic.cell_magic
    def sbash(self, line='', cell=None):
        if not self.loggedin():
            return
        _, stdout, stderr = self._ssh.exec_command(cell.format(**self.shell.user_ns))
        for line in stdout:
            print(line.strip('\n'), file=sys.stdout)
        for line in stderr:
            print(line.strip('\n'), file=sys.stderr)

    @magic.line_magic
    def slogin(self, line=''):
        self.logout()
        opts, _ = self.parse_options(line, 's:u:p:', 'server=', 'username=', 'password=')
        server = opts.get('s', None) or opts.get('server', None)
        username = opts.get('u', None) or opts.get('username', None)
        password = opts.get('p', None) or opts.get('password', None)
        assert server is not None, 'Server address is required'
        if username is None:
            username = input('JHED Username: ')
        if password is None:
            password = getpass('JHED Password: ')
        self.login(server, username, password)
        return self

    @magic.line_magic
    def slogout(self, line=''):
        if self._ssh is not None:
            print('Logging out of {}'.format(self._ssh.get_host_keys().keys()[0]))
        self.logout()

    @magic.line_magic
    def srepeat(self, line=''):
        if not self.loggedin():
            return
        try:
            while True:
                clear_output(wait=True)
                self.sbash(cell=line)
                time.sleep(1)
        except:
            pass


def load_ipython_extension(ipython):
    ipython.register_magics(Slurm)
