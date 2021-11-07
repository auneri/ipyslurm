import datetime
import getpass
import logging
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

    def login(self, server, username=None, password=None, **kwargs):
        if username is None:
            username = getpass.getuser()
        logging.getLogger('ipyslurm.slurm').debug(f'Logging in to {username}@{server}')
        self.ssh = ssh.SSH(server, username, password, **kwargs)
        return self

    def logout(self):
        if self.ssh is not None:
            logging.getLogger('ipyslurm.slurm').debug(f'Logging out of {self.ssh.server}')
            self.ssh = None

    def sbatch(self, lines, args=None):
        self._verify_login()
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
        stdouts = self.ssh.exec_command(command_args)
        for stdout in stdouts:
            args = re.sub('\\{(.+?)\\}', stdout, args, count=1)
        if lines:
            command = ['sbatch {} --wrap="{}"'.format(args, '\n'.join(command))]
        else:
            command = [f'sbatch {args}']
        stdouts = self.ssh.exec_command(command_init + command)
        if not stdouts or not stdouts[-1].startswith('Submitted batch job '):
            raise IOError('\n'.join(stdouts))
        logging.getLogger('ipyslurm.slurm').debug(stdouts[-1])
        return int(stdouts[-1].lstrip('Submitted batch job '))

    def script(self, lines, *args, **kwargs):
        self._verify_login()
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
                self.ssh.exec_command(command_init)
            stdouts = self.ssh.exec_command(command, *args, **kwargs)
            for stdout in stdouts:
                logging.getLogger('ipyslurm.slurm').debug(stdout)
            return '\n'.join(stdouts)
        finally:
            if command_del:
                self.ssh.exec_command(command_del)

    def sftp(self, lines, quiet=False):
        self._verify_login()
        ftp = sftp.SFTP(self.ssh)
        ftp.exec_commands(lines, quiet)

    def shell(self):
        self._verify_login()
        self.ssh.invoke_shell()

    def _verify_login(self):
        if self.ssh is None:
            raise AuthenticationException('Not logged in to a server')
