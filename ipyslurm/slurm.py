import datetime
import logging
import re
import shlex

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
        return f'Logged in to {self.ssh.server}' if self.ssh is not None else 'Not logged in to a server'

    def command(self, lines, delete=True):
        self._verify_login()
        if isinstance(lines, str):
            lines = lines.splitlines()
        shebangs = [i for i, x in enumerate(lines) if x.startswith('#!')]
        command = lines[:shebangs[0]] if shebangs else lines
        command_init = []
        command_del = []
        for i, j in zip(shebangs, shebangs[1:] + [None]):
            timestamp = datetime.datetime.now().strftime(f'%Y%m%d_%H%M%S_{i}')
            script = '\n'.join(x.replace("'", "'\"'\"'") for x in lines[slice(i, j)])
            command_init += [
                'mkdir -p ~/.ipyslurm',
                f"echo '{script}' > ~/.ipyslurm/script_{timestamp}",
                f'chmod +x ~/.ipyslurm/script_{timestamp}']
            command += [f'~/.ipyslurm/script_{timestamp}']
            if delete:
                command_del += [f'rm ~/.ipyslurm/script_{timestamp}']
        try:
            if command_init:
                self.ssh.exec_command(command_init)
            stdouts = self.ssh.exec_command(command)
            for stdout in stdouts:
                logging.getLogger('ipyslurm.slurm').debug(stdout)
            return '\n'.join(stdouts)
        finally:
            if command_del:
                self.ssh.exec_command(command_del)

    def interact(self):
        self._verify_login()
        self.ssh.invoke_shell()

    def login(self, server, username, password=None, **kwargs):
        logging.getLogger('ipyslurm.slurm').debug(f'Logging in to {username}@{server}')
        self.ssh = ssh.SSH(server, username, password, **kwargs)

    def logout(self):
        if self.ssh is not None:
            logging.getLogger('ipyslurm.slurm').debug(f'Logging out of {self.ssh.server}')
            self.ssh = None

    def sbatch(self, lines, args=None):
        self._verify_login()
        if isinstance(lines, str):
            lines = lines.splitlines()
        if args is None:
            args = []
        elif isinstance(args, str):
            args = shlex.split(args, posix=False)
        args = ' '.join(list(args) + [x.replace('#SBATCH', '').strip() for x in lines if x.startswith('#SBATCH')])
        lines = [x.replace("'", "'\"'\"'") for x in lines if not x.startswith('#SBATCH')]
        shebangs = [i for i, x in enumerate(lines) if x.startswith('#!')]
        command = lines[:shebangs[0]] if shebangs else lines
        command_init = []
        for i, j in zip(shebangs, shebangs[1:] + [None]):
            timestamp = datetime.datetime.now().strftime(f'%Y%m%d_%H%M%S_{i}')
            script = '\n'.join(lines[slice(i, j)])
            command_init += [
                'mkdir -p ~/.ipyslurm',
                f"echo '{script}' > ~/.ipyslurm/sbatch_{timestamp}",
                f'chmod +x ~/.ipyslurm/sbatch_{timestamp}']
            command += [f'~/.ipyslurm/sbatch_{timestamp}']
        command_args = [match.group(1) for match in re.finditer('\\{(.+?)\\}', args)]
        if command_args:
            stdouts = self.ssh.exec_command(command_args)
            for stdout in stdouts:
                args = re.sub('\\{(.+?)\\}', stdout, args, count=1)
        if lines:
            command = ["sbatch {} --wrap='{}'".format(args, '\n'.join(command))]
        else:
            command = [f'sbatch {args}']
        stdouts = self.ssh.exec_command(command_init + command)
        if not stdouts or not stdouts[-1].startswith('Submitted batch job '):
            raise RuntimeError('\n'.join(stdouts))
        logging.getLogger('ipyslurm.slurm').debug(stdouts[-1])
        return int(stdouts[-1].split()[-1])

    def sftp(self, lines):
        self._verify_login()
        if isinstance(lines, str):
            lines = lines.splitlines()
        lines = [x for x in lines if x.strip() and not x.lstrip().startswith('#')]
        ftp = sftp.SFTP(self.ssh)
        ftp.exec_commands(lines)

    def _verify_login(self):
        if self.ssh is None:
            raise AuthenticationException('Not logged in to a server')
