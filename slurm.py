from __future__ import absolute_import, division, print_function

import getpass
import os
import platform
import sys
import time
import timeit

import paramiko
from IPython.core import magic
from IPython.display import clear_output
from six import print_ as print
from six.moves import input

from PythonTools import distributed


def interact(channel):
    if platform.system() == 'Windows':
        import threading

        def writeall(channel_):
            while True:
                stdout = channel_.recv(256)
                if not stdout:
                    sys.stdout.flush()
                    break
                sys.stdout.write(stdout)
                sys.stdout.flush()
        writer = threading.Thread(target=writeall, args=(channel,))
        writer.start()
        while True:
            stdin = input()
            if stdin in ('exit', 'quit', 'q'):
                break
            channel.send('{}\n'.format(stdin))
    else:
        import select
        import socket
        import termios
        import tty
        tty_prev = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            channel.setblocking(False)
            while True:
                r, w, e = select.select([channel, sys.stdin], [], [])
                if channel in r:
                    try:
                        stdout = paramiko.py3compat.u(channel.recv(1024))
                        if not stdout:
                            sys.stdout.flush()
                            break
                        sys.stdout.write(stdout)
                        sys.stdout.flush()
                    except socket.timeout:
                        pass
                if sys.stdin in r:
                    stdin = input()
                    if stdin in ('exit', 'quit', 'q'):
                        break
                    channel.send('{}\n'.format(stdin))
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, tty_prev)


@magic.magics_class
class Slurm(magic.Magics):

    def __init__(self, *args, **kwargs):
        super(Slurm, self).__init__(*args, **kwargs)
        self._ssh = None
        self._ssh_data = None

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
                    clear_output(wait=True)
                    if tail and details['JobState'] in ('RUNNING', 'COMPLETING', 'COMPLETED'):
                        self._ssh.exec_command('tail --lines=5 {}'.format(details['StdOut']))
                    else:
                        for key in keys:
                            print('{1:>{0}}: {2}'.format(fill, key, details[key]))
                    if details['JobState'] not in ('PENDING', 'CONFIGURING', 'RUNNING', 'COMPLETING'):
                        break
            except KeyboardInterrupt:
                self._ssh.exec_command('scancel {}'.format(job))

    @magic.line_magic
    def sinteract(self, line=''):
        channel = self._ssh.invoke_shell()
        interact(channel)
        channel.close()

    @magic.line_magic
    def slogin(self, line=''):
        opts, _ = self.parse_options(line, 's:u:p:d:', 'server=', 'username=', 'password=', 'data-server=')
        server = opts.get('s', None) or opts.get('server', None)
        username = opts.get('u', None) or opts.get('username', None)
        password = opts.get('p', None) or opts.get('password', None)
        server_data = opts.get('d', None) or opts.get('data-server', None)
        if server is None:
            server = input('Server: ')
        if username is None:
            username = getpass.getuser()
        if server_data is not None:
            try:
                print('Logging in to {}@{}'.format(username, server_data))
                self._ssh_data = distributed.SSHClient()
                self._ssh_data.connect(server_data, username, password, allow_agent=False, look_for_keys=False)
                self._ssh_data.get_transport().set_keepalive(30)
                print('Please wait for a new verification code before logging in to {}!'.format(server))
            except:
                self._ssh_data = None
                raise
        try:
            print('Logging in to {}@{}'.format(username, server))
            self._ssh = distributed.SSHClient()
            self._ssh.connect(server, username, password, allow_agent=False, look_for_keys=False)
            self._ssh.get_transport().set_keepalive(30)
        except:
            self._ssh = None
            raise
        return self

    @magic.line_magic
    def slogout(self, line=''):
        if self._ssh is not None:
            print('Logging out of {}'.format(self._ssh.get_server()))
        self._ssh = None
        if self._ssh_data is not None:
            print('Logging out of {}'.format(self._ssh_data.get_server()))
        self._ssh_data = None

    @magic.cell_magic
    def ssftp(self, line='', cell=None):
        """Commands: cd, chmod, chown, get, ln, ls, mkdir, put, pwd, rename, rm, rmdir, symlink.

        See interactive commands section of http://man.openbsd.org/sftp for details.
        """
        if self._ssh is None:
            raise paramiko.AuthenticationException('Please login using %slogin')
        ssh = self._ssh if self._ssh_data is None else self._ssh_data
        sftp = ssh.open_sftp()
        sftp.chdir(ssh.exec_command('pwd', verbose=False)[0][0])
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
                'lls': 'listdir',
                'ln': 'symlink',
                'lpwd': 'getcwd',
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
                if argv[0] in ('lls', 'lpwd'):
                    output = getattr(os, command)(*argv[1:])
                else:
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
