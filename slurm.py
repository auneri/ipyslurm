from __future__ import absolute_import, division, print_function

import sys
from getpass import getpass

import paramiko
from IPython.core import magic
from six import print_ as print
from six.moves import input


@magic.magics_class
class Slurm(magic.Magics):

    @magic.cell_magic
    def sexec(self, line='', cell=None):
        opts, _ = self.parse_options(line, 's:u:p:', 'server=', 'username=', 'password=')
        server = opts.get('s', None) or opts.get('server', None)
        username = opts.get('u', None) or opts.get('username', None)
        password = opts.get('p', None) or opts.get('password', None)
        assert server is not None, 'Server address is required'
        if username is None:
            username = input('JHED Username: ')
        if password is None:
            password = getpass('JHED Password: ')
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server, username=username, password=password)
        _, stdout, stderr = ssh.exec_command(cell.format(**self.shell.user_ns))
        for line in stdout:
            print(line.strip('\n'), file=sys.stdout)
        for line in stderr:
            print(line.strip('\n'), file=sys.stderr)
        ssh.close()


def load_ipython_extension(ipython):
    ipython.register_magics(Slurm)
