import datetime
import getpass
import re
import sys
from contextlib import contextmanager

from paramiko import AuthenticationException

from . import sftp, ssh


class Slurm:

    def __init__(self, *args, **kwargs):
        self.ssh = None
        if len(args) or len(kwargs):
            self.login(*args, **kwargs)

    def __del__(self):
        self.logout()

    def __repr__(self):
        servers = [x.server for x in (self.ssh,) if x is not None]
        return 'Logged in to {}'.format(' and '.join(servers)) if servers else 'Not logged in to server'

    def login(self, server, username=None, password=None):
        if username is None:
            username = getpass.getuser()
        print(f'Logging in to {username}@{server}')
        self.ssh = ssh.SSH(server, username, password)
        self.ssh.get_transport().set_keepalive(30)
        return self

    def logout(self):
        if self.ssh is not None:
            print(f'Logging out of {self.ssh.server}')
            self.ssh = None

    def sbatch(self, lines, args=None):
        if self.ssh is None:
            raise AuthenticationException('Not logged in to server')
        if args is None:
            args = []
        args = ' '.join(args + [x.replace('#SBATCH', '').strip() for x in lines if x.startswith('#SBATCH')])
        lines = [x.replace('\\', '\\\\\\').replace('$', '\\$').replace('"', '\\"') for x in lines if not x.startswith('#SBATCH')]
        shebangs = [i for i, x in enumerate(lines) if x.startswith('#!')]
        command = lines[:shebangs[0]] if shebangs else lines
        command_init = []
        for i, j in zip(shebangs, shebangs[1:] + [None]):
            timestamp = datetime.datetime.now().strftime(f'%Y%m%d_%H%M%S_{i}')
            script = '\n'.join(lines[slice(i, j)])
            command_init += [
                'mkdir -p ~/.ipyslurm',
                f'echo -e "{script}" > ~/.ipyslurm/sbatch_{timestamp}',
                f'chmod +x ~/.ipyslurm/sbatch_{timestamp}']
            command += [f'~/.ipyslurm/sbatch_{timestamp}']
        command_args = [match.group(1) for match in re.finditer('\\{(.+?)\\}', args)]
        stdouts, stderrs = self.ssh.exec_command(command_args, verbose=False)
        if stderrs:
            raise IOError('\n'.join(stderrs))
        for stdout in stdouts:
            args = re.sub('\\{(.+?)\\}', stdout, args, count=1)
        if lines:
            command = ['sbatch {} --wrap="{}"'.format(args, '\n'.join(command))]
        else:
            command = [f'sbatch {args}']
        stdouts, _ = self.ssh.exec_command(command_init + command)
        if not stdouts or not stdouts[-1].startswith('Submitted batch job '):
            raise IOError('\n'.join(stdouts))
        return int(stdouts[-1].lstrip('Submitted batch job '))

    def script(self, lines, *args, **kwargs):
        if self.ssh is None:
            raise AuthenticationException('Not logged in to server')
        shebangs = [i for i, x in enumerate(lines) if x.startswith('#!')]
        command = lines[:shebangs[0]] if shebangs else lines
        command_init = []
        command_del = []
        for i, j in zip(shebangs, shebangs[1:] + [None]):
            timestamp = datetime.datetime.now().strftime(f'%Y%m%d_%H%M%S_{i}')
            script = '\n'.join(x.replace('\\', '\\\\\\').replace('$', '\\$').replace('"', '\\"') for x in lines[slice(i, j)])
            command_init += [
                'mkdir -p ~/.ipyslurm',
                f'echo -e "{script}" > ~/.ipyslurm/sbash_{timestamp}',
                f'chmod +x ~/.ipyslurm/sbash_{timestamp}']
            command_del += [f'rm ~/.ipyslurm/sbash_{timestamp}']
            command += [f'~/.ipyslurm/sbash_{timestamp}']
        try:
            if command_init:
                self.ssh.exec_command(command_init, verbose=False)
            while True:
                yield self.ssh.exec_command(command, *args, **kwargs)
        finally:
            if command_del:
                self.ssh.exec_command(command_del, verbose=False)

    def sftp(self, lines, quiet=False):
        if self.ssh is None:
            raise AuthenticationException('Not logged in to server')
        ftp = sftp.SFTP(self.ssh)
        ftp.exec_commands(lines, quiet)

    def shell(self):
        self.ssh.invoke_shell()
