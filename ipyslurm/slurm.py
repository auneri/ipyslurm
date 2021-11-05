import datetime
import getpass
import re
import sys
from contextlib import contextmanager

from paramiko import AuthenticationException

from .ssh import SSHClient


class Slurm:

    def __init__(self):
        self._ssh = None
        self._ssh_data = None

    def __del__(self):
        self.logout()

    def __repr__(self):
        servers = [x.get_server() for x in (self._ssh, self._ssh_data) if x is not None]
        return 'Logged in to {}'.format(' and '.join(servers)) if servers else 'Not logged in to server'

    def login(self, server, username=None, password=None, server_data=None):
        if username is None:
            username = getpass.getuser()
        try:
            print('Logging in to {}@{}'.format(username, server))
            self._ssh = SSHClient()
            self._ssh.connect(server, username, password)
            self._ssh.get_transport().set_keepalive(30)
        except:  # noqa: E722
            self._ssh = None
            raise
        if server_data is not None:
            try:
                sys.stdout.flush()
                print('Please wait for a new verification code before logging in to {}'.format(server_data), file=sys.stderr, flush=True)
                print('Logging in to {}@{}'.format(username, server_data))
                self._ssh_data = SSHClient()
                self._ssh_data.connect(server_data, username, password)
                self._ssh_data.get_transport().set_keepalive(30)
            except:  # noqa: E722
                self._ssh_data = None
                raise
        return self

    def logout(self):
        if self._ssh is not None:
            print('Logging out of {}'.format(self._ssh.get_server()))
            self._ssh = None
        if self._ssh_data is not None:
            print('Logging out of {}'.format(self._ssh_data.get_server()))
            self._ssh_data = None

    def sbatch(self, lines, args=None):
        if self._ssh is None:
            raise AuthenticationException('Not logged in to server')
        if args is None:
            args = []
        args = ' '.join(args + [x.replace('#SBATCH', '').strip() for x in lines if x.startswith('#SBATCH')])
        lines = [x.replace('\\', '\\\\\\').replace('$', '\\$').replace('"', '\\"') for x in lines if not x.startswith('#SBATCH')]
        shebangs = [i for i, x in enumerate(lines) if x.startswith('#!')]
        command = lines[:shebangs[0]] if shebangs else lines
        command_init = []
        for i, j in zip(shebangs, shebangs[1:] + [None]):
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_{}'.format(i))
            script = '\n'.join(lines[slice(i, j)])
            command_init += [
                'mkdir -p ~/.ipyslurm',
                'echo -e "{}" > ~/.ipyslurm/sbatch_{}'.format(script, timestamp),
                'chmod +x ~/.ipyslurm/sbatch_{}'.format(timestamp)]
            command += ['~/.ipyslurm/sbatch_{}'.format(timestamp)]
        command_args = [match.group(1) for match in re.finditer('\\{(.+?)\\}', args)]
        stdouts, stderrs = self._ssh.exec_command(command_args, verbose=False)
        if stderrs:
            raise IOError('\n'.join(stderrs))
        for stdout in stdouts:
            args = re.sub('\\{(.+?)\\}', stdout, args, count=1)
        if lines:
            command = ['sbatch {} --wrap="{}"'.format(args, '\n'.join(command))]
        else:
            command = ['sbatch {}'.format(args)]
        stdouts, _ = self._ssh.exec_command(command_init + command)
        if not stdouts or not stdouts[-1].startswith('Submitted batch job '):
            raise IOError('\n'.join(stdouts))
        return int(stdouts[-1].lstrip('Submitted batch job '))

    def script(self, lines, *args, **kwargs):
        if self._ssh is None:
            raise AuthenticationException('Not logged in to server')
        shebangs = [i for i, x in enumerate(lines) if x.startswith('#!')]
        command = lines[:shebangs[0]] if shebangs else lines
        command_init = []
        command_del = []
        for i, j in zip(shebangs, shebangs[1:] + [None]):
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_{}'.format(i))
            script = '\n'.join(x.replace('\\', '\\\\\\').replace('$', '\\$').replace('"', '\\"') for x in lines[slice(i, j)])
            command_init += [
                'mkdir -p ~/.ipyslurm',
                'echo -e "{}" > ~/.ipyslurm/sbash_{}'.format(script, timestamp),
                'chmod +x ~/.ipyslurm/sbash_{}'.format(timestamp)]
            command_del += ['rm ~/.ipyslurm/sbash_{}'.format(timestamp)]
            command += ['~/.ipyslurm/sbash_{}'.format(timestamp)]
        try:
            if command_init:
                self._ssh.exec_command(command_init, verbose=False)
            while True:
                yield self._ssh.exec_command(command, *args, **kwargs)
        finally:
            if command_del:
                self._ssh.exec_command(command_del, verbose=False)

    @contextmanager
    def sftp(self):
        if self._ssh is None:
            raise AuthenticationException('Not logged in to server')
        ssh = self._ssh_data or self._ssh
        ftp = ssh.open_sftp()
        try:
            yield ssh, ftp
        finally:
            ftp.close()

    def shell(self):
        self._ssh.invoke_shell()
