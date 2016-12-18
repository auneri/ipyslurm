from __future__ import absolute_import, division, print_function

import sys
import time
from datetime import datetime
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

    def __repr__(self):
        if self._ssh is not None:
            return 'Logged in to {}'.format(self._ssh.get_host_keys().keys()[0])

    def execute(self, command, verbose=True):
        _, stdout, stderr = self._ssh.exec_command(command)
        stdouts = []
        stderrs = []
        for line in stdout:
            if verbose:
                print(line.strip('\n'), file=sys.stdout)
            stdouts.append(line.strip('\n'))
        for line in stderr:
            if verbose:
                print(line.strip('\n'), file=sys.stderr)
            stderrs.append(line.strip('\n'))
        return stdouts, stderrs

    def loggedin(self):
        if self._ssh is None:
            raise paramiko.AuthenticationException('Please login to cluster using %slogin')

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

    @magic.line_magic
    @magic.cell_magic
    def sbash(self, line='', cell=None):
        self.loggedin()
        self.execute(cell or line)

    @magic.cell_magic
    def sbatch(self, line='', cell=None):
        self.loggedin()
        self.execute('sbatch {} --wrap="{}"'.format(line, cell.replace('$', r'\$')))

    @magic.line_magic
    def slogin(self, line=''):
        self.logout()
        opts, _ = self.parse_options(line, 's:u:p:', 'server=', 'username=', 'password=')
        server = opts.get('s', None) or opts.get('server', None)
        username = opts.get('u', None) or opts.get('username', None)
        password = opts.get('p', None) or opts.get('password', None)
        assert server is not None, 'Server address is required'
        if server is None:
            server = input('Server: ')
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

    @magic.cell_magic
    def srepeat(self, line='', cell=None):
        opts, _ = self.parse_options(line, 'p:t:', 'period=', 'timeout=')
        period = opts.get('p', None) or opts.get('period', None)
        timeout = opts.get('t', None) or opts.get('timeout', None)
        self.loggedin()
        period = 1.0 if period is None else float(period)
        timeout = None if timeout is None else float(timeout)
        start = datetime.now()
        try:
            while True:
                clear_output(wait=True)
                self.execute(cell or line)
                elapsed = (datetime.now() - start).total_seconds()
                if timeout is not None and elapsed > timeout:
                    print('\nTimed out after {:.1f} seconds'.format(elapsed))
                    break
                time.sleep(period)
        except KeyboardInterrupt:
            pass

    @magic.cell_magic
    def ssftp(self, line='', cell=None):
        """Commands: cd, chmod, chown, get, ln, ls, mkdir, put, pwd, rename, rm, rmdir, symlink.
        See interactive commands section of http://man.openbsd.org/sftp for details.
        """
        self.loggedin()
        sftp = self._ssh.open_sftp()
        sftp.chdir(self.execute('pwd', verbose=False)[0][0])
        for line in cell.splitlines():
            argv = line.split()
            if not argv:
                continue
            if argv[0].startswith('#'):
                continue
            commands = {
                'cd': 'chdir',
                'chmod': 'chmod',
                'chown': 'chown',
                'get': 'get',
                'ln': 'symlink',
                'ls': 'listdir',
                'mkdir': 'mkdir',
                'put': 'put',
                'pwd': 'getcwd',
                'rename': 'rename',
                'rm': 'remove',
                'rmdir': 'rmdir',
                'symlink': 'symlink'}
            if argv[0] in commands:
                command = commands[argv[0]]
                output = getattr(sftp, command)(*argv[1:])
                if command == 'getcwd':
                    print(output)
                elif command == 'listdir':
                    print('\n'.join(sorted(output)))
            else:
                raise SyntaxError('Command "{}" is not supported'.format(argv[0]))
        sftp.close()


def load_ipython_extension(ipython):
    ipython.register_magics(Slurm)
