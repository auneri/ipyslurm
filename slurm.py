from __future__ import absolute_import, division, print_function

import getpass
import time
import timeit

import paramiko
from IPython.core import magic
from IPython.display import clear_output
from six import print_ as print
from six.moves import input

from PythonTools.distributed import SSHClient


@magic.magics_class
class Slurm(magic.Magics):

    def __init__(self, *args, **kwargs):
        super(Slurm, self).__init__(*args, **kwargs)
        self._ssh = None

    def __del__(self):
        self.slogout()
        super(Slurm, self).__del__()

    def __repr__(self):
        if self._ssh is not None:
            return 'Logged in to {}'.format(self._ssh.get_server())

    @magic.cell_magic
    def sbatch(self, line='', cell=None):
        if self._ssh is None:
            raise paramiko.AuthenticationException('Please login using %slogin')
        job = None
        wait = '--wait' in line
        if wait:
            line = line.replace('--wait', '')
        tail = '--tail' in line
        if tail:
            line = line.replace('--tail', '')
        block = wait or tail
        cell = cell.replace('\\', '\\\\\\').replace('$', '\\$').replace('"', '\\"')
        if cell.startswith('#!'):
            self._ssh.exec_command('echo -e "{}" > ~/.slurm.magic'.format(cell))
            stdouts, _ = self._ssh.exec_command('sbatch {} ~/.slurm.magic'.format(line))
            self._ssh.exec_command('rm ~/.slurm.magic')
        else:
            stdouts, _ = self._ssh.exec_command('sbatch {} --wrap="{}"'.format(line, cell))
        if stdouts and stdouts[-1].startswith('Submitted batch job '):
            job = int(stdouts[-1].lstrip('Submitted batch job '))
        if block and job is not None:
            keys = 'JobId', 'JobName', 'JobState', 'SubmitTime', 'StartTime', 'RunTime'
            fill = max(len(i) for i in keys)
            try:
                while True:
                    stdouts, _ = self._ssh.exec_command('scontrol show jobid {}'.format(job), verbose=False)
                    details = dict(line.split('=', 1) for line in '\n'.join(stdouts).split())
                    if details['JobState'] == 'COMPLETED':
                        break
                    clear_output(wait=True)
                    if tail and details['JobState'] == 'RUNNING':
                        self._ssh.exec_command('tail --lines=5 {}'.format(details['StdOut']))
                    else:
                        for key in keys:
                            print('{1:>{0}}: {2}'.format(fill, key, details[key]))
            except KeyboardInterrupt:
                self._ssh.exec_command('scancel {}'.format(job))

    @magic.line_magic
    def slogin(self, line=''):
        opts, _ = self.parse_options(line, 's:u:p:', 'server=', 'username=', 'password=')
        server = opts.get('s', None) or opts.get('server', None)
        username = opts.get('u', None) or opts.get('username', None)
        password = opts.get('p', None) or opts.get('password', None)
        if server is None:
            server = input('Server: ')
        if username is None:
            username = getpass.getuser()
        try:
            print('Logging into {}@{}'.format(username, server))
            self._ssh = SSHClient()
            self._ssh.connect(server, username, password)
        except paramiko.AuthenticationException:
            self._ssh = None
            raise
        return self

    @magic.line_magic
    def slogout(self, line=''):
        if self._ssh is not None:
            print('Logging out of {}'.format(self._ssh.get_server()))
        self._ssh = None

    @magic.cell_magic
    def ssftp(self, line='', cell=None):
        """Commands: cd, chmod, chown, get, ln, ls, mkdir, put, pwd, rename, rm, rmdir, symlink.

        See interactive commands section of http://man.openbsd.org/sftp for details.
        """
        if self._ssh is None:
            raise paramiko.AuthenticationException('Please login using %slogin')
        sftp = self._ssh.open_sftp()
        sftp.chdir(self._ssh.exec_command('pwd', verbose=False)[0][0])
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

    @magic.cell_magic
    def sshell(self, line='', cell=None):
        if self._ssh is None:
            raise paramiko.AuthenticationException('Please login using %slogin')
        opts, _ = self.parse_options(line, 'p:t:', 'period=', 'timeout=')
        period = opts.get('p', None) or opts.get('period', None)
        timeout = opts.get('t', None) or opts.get('timeout', None)
        if period is not None:
            period = float(period)
        if timeout is not None:
            timeout = float(timeout)
        if cell.startswith('#!'):
            cell = cell.replace('\\', '\\\\\\').replace('$', '\\$').replace('"', '\\"')
            self._ssh.exec_command('echo -e "{}" > ~/.slurm.magic'.format(cell))
            self._ssh.exec_command('chmod +x ~/.slurm.magic'.format(cell))
        start = timeit.default_timer()
        try:
            while True:
                clear_output(wait=True)
                if cell.startswith('#!'):
                    self._ssh.exec_command('~/.slurm.magic'.format(line))
                else:
                    self._ssh.exec_command(cell)
                elapsed = timeit.default_timer() - start
                if timeout is not None and elapsed > timeout:
                    print('\nTimed out after {:.1f} seconds'.format(elapsed))
                    break
                if period is not None:
                    time.sleep(period)
                else:
                    break
        except KeyboardInterrupt:
            pass
        finally:
            if cell.startswith('#!'):
                self._ssh.exec_command('rm ~/.slurm.magic')


def load_ipython_extension(ipython):
    ipython.register_magics(Slurm)
