import datetime
import itertools
import logging
import re
import shlex

from IPython.display import clear_output
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
            return '\n'.join(self.ssh.exec_command(command))
        finally:
            if command_del:
                self.ssh.exec_command(command_del)

    def disk_usage(self, directory='~', depth=0):
        print(self.command(f'df --human-readable {directory}'))
        print('Size Directory')
        print(self.command(f'du --human-readable --max-depth {depth} {directory} | sort -k2,2 -k1,1hr'))

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

    def scancel(self, job):
        self.command(f'scancel {job}')

    def scontrol_show_job(self, job):
        stdouts = self.ssh.exec_command(f'scontrol show job {job} --details')
        details = [list(x) for _, x in itertools.groupby(stdouts, key=''.__ne__)][::2]
        details = [re.split(r'\s*(\w+)=', ' '.join(x)) for x in details]
        details = [dict([x[i:i+2] for i in range(1, len(x), 2)]) for x in details]
        return sorted(details, key=lambda x: int(x['ArrayTaskId']) if 'ArrayTaskId' in x and x['ArrayTaskId'].isnumeric() else 0)

    def sftp(self, lines):
        self._verify_login()
        if isinstance(lines, str):
            lines = lines.splitlines()
        lines = [x for x in lines if x.strip() and not x.lstrip().startswith('#')]
        ftp = sftp.SFTP(self.ssh)
        ftp.exec_commands(lines)

    def squeue(self, output_format=None):
        if output_format is None:
            output_format = '%.20j %.15i %.7M %.10l %.7u %.9P %.8T %R'
        print(self.command(f'squeue --format "{output_format}"'))

    def tail(self, job, lines=1, clear=True):
        while True:
            details = self.scontrol_show_job(job)
            stdouts = []
            for detail in details:
                stdouts.append(self.ssh.exec_command(f'if test -f "{detail["StdOut"]}"; then tail --lines={lines} {detail["StdOut"]}; fi'))
            if clear:
                clear_output(wait=True)
            for i, detail in enumerate(details):
                jobname = detail['JobName']
                if 'ArrayTaskId' in detail:
                    jobname = f'{jobname} [{detail["ArrayTaskId"]}]'
                for stdout in stdouts[i]:
                    print(f'{jobname}: {stdout}', flush=True)
                if len(stdouts[i]) == 0:
                    print(f'{jobname}: {detail["JobState"]}', flush=True)
            if all(x['JobState'] not in ('COMPLETING', 'CONFIGURING', 'PENDING', 'RUNNING') for x in details):
                break

    def writefile(self, filepath, lines, append=False):
        if isinstance(lines, str):
            lines = lines.splitlines()
        redirect = '>>' if append else '>'
        self.command([f'cat << \\EOF {redirect} {filepath}'] + lines + ['EOF'])

    def _verify_login(self):
        if self.ssh is None:
            raise AuthenticationException('Not logged in to a server')
