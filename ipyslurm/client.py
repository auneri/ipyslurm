#!/usr/bin/env python

from __future__ import absolute_import, division, print_function

import datetime
import getpass
import platform
import re
import sys
from contextlib import contextmanager

import paramiko
from paramiko import AuthenticationException
from six import print_ as print  # noqa: A001
from six import string_types


class Slurm(object):

    def __init__(self):
        self._ssh = None
        self._ssh_data = None

    def __del__(self):
        self.logout()

    def __repr__(self):
        servers = [ssh.get_server() for ssh in [self._ssh, self._ssh_data] if ssh is not None]
        return 'Logged in to {}'.format(' and '.join(servers)) if servers else 'Not logged in to server'

    def bash(self, lines, *args, **kwargs):
        if self._ssh is None:
            raise AuthenticationException('Not logged in to server')
        shebangs = [i for i, line in enumerate(lines) if line.startswith('#!')]
        command = lines[:shebangs[0]] if shebangs else lines
        command_init = []
        command_del = []
        for i, j in zip(shebangs, shebangs[1:] + [None]):
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_{}'.format(i))
            script = '\n'.join(line.replace('\\', '\\\\\\').replace('$', '\\$').replace('"', '\\"') for line in lines[slice(i, j)])
            command_init += [
                'mkdir -p ~/.ipyslurm',
                'echo -e "{}" > ~/.ipyslurm/bash_{}'.format(script, timestamp),
                'chmod +x ~/.ipyslurm/bash_{}'.format(timestamp)]
            command_del += ['rm ~/.ipyslurm/bash_{}'.format(timestamp)]
            command += ['~/.ipyslurm/bash_{}'.format(timestamp)]
        try:
            if command_init:
                self._ssh.exec_command(command_init, verbose=False)
            while True:
                yield self._ssh.exec_command(command, *args, **kwargs)
        finally:
            if command_del:
                self._ssh.exec_command(command_del, verbose=False)

    def batch(self, lines, args=None):
        if self._ssh is None:
            raise AuthenticationException('Not logged in to server')
        if args is None:
            args = []
        args = ' '.join(args + [line.replace('#SBATCH', '').strip() for line in lines if line.startswith('#SBATCH')])
        lines = [line.replace('\\', '\\\\\\').replace('$', '\\$').replace('"', '\\"') for line in lines if not line.startswith('#SBATCH')]
        shebangs = [i for i, line in enumerate(lines) if line.startswith('#!')]
        command = lines[:shebangs[0]] if shebangs else lines
        command_init = []
        for i, j in zip(shebangs, shebangs[1:] + [None]):
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_{}'.format(i))
            script = '\n'.join(lines[slice(i, j)])
            command_init += [
                'mkdir -p ~/.ipyslurm',
                'echo -e "{}" > ~/.ipyslurm/batch_{}'.format(script, timestamp),
                'chmod +x ~/.ipyslurm/batch_{}'.format(timestamp)]
            command += ['~/.ipyslurm/batch_{}'.format(timestamp)]
        command_args = [match.group(1) for match in re.finditer('\{(.+?)\}', args)]
        stdouts, stderrs = self._ssh.exec_command(command_args, verbose=False)
        if stderrs:
            raise IOError('\n'.join(stderrs))
        for stdout in stdouts:
            args = re.sub('\{(.+?)\}', stdout, args, count=1)
        command = ['sbatch {} --wrap="{}"'.format(args, '\n'.join(command))]
        stdouts, _ = self._ssh.exec_command(command_init + command)
        if not stdouts or not stdouts[-1].startswith('Submitted batch job '):
            raise IOError('\n'.join(stdouts))
        return int(stdouts[-1].lstrip('Submitted batch job '))

    @contextmanager
    def ftp(self):
        if self._ssh is None:
            raise AuthenticationException('Not logged in to server')
        ssh = self._ssh_data or self._ssh
        ftp = ssh.open_sftp()
        try:
            yield ssh, ftp
        finally:
            ftp.close()

    def interact(self):
        self._ssh.invoke_shell()

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


class SSHClient(paramiko.SSHClient):

    def __init__(self, *args, **kwargs):
        super(SSHClient, self).__init__(*args, **kwargs)
        self.load_system_host_keys()
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._server = None

    def __del__(self):
        self.close()

    def connect(self, server, username, password=None, *args, **kwargs):
        try:
            super(SSHClient, self).connect(server, username=username, password=password, *args, **kwargs)
        except (AuthenticationException, paramiko.SSHException):
            def handler(title, instructions, prompt_list):
                if title:
                    print(title.strip())
                if instructions:
                    print(instructions.strip())
                return [show_input and input(prompt.strip()) or getpass.getpass(prompt.strip()) for prompt, show_input in prompt_list]
            self.get_transport().auth_interactive_dumb(username=username, handler=handler)
        self._server = server

    def exec_command(self, command, *args, **kwargs):
        verbose = kwargs.pop('verbose', True)
        if not isinstance(command, string_types):
            command = '\n'.join(command)
        _, stdout, stderr = super(SSHClient, self).exec_command(command, *args, **kwargs)
        stdouts = [line.strip('\n') for line in stdout]
        stderrs = [line.strip('\n') for line in stderr]
        if verbose:
            if stdouts:
                print('\n'.join(stdouts), file=sys.stdout)
            if stderrs:
                print('\n'.join(stderrs), file=sys.stderr)
        return stdouts, stderrs

    def get_server(self):
        return self._server

    def invoke_shell(self, *args, **kwargs):
        channel = super(SSHClient, self).invoke_shell(*args, **kwargs)
        if platform.system() == 'Windows':
            import threading

            def writeall(channel_):
                while True:
                    stdout = paramiko.py3compat.u(channel_.recv(256))
                    if not stdout:
                        sys.stdout.flush()
                        break
                    sys.stdout.write(stdout)
                    sys.stdout.flush()
            writer = threading.Thread(target=writeall, args=(channel,))
            writer.start()

            while True:
                stdin = input()
                if stdin in ['exit', 'quit', 'q']:
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
                        if stdin in ['exit', 'quit', 'q']:
                            break
                        channel.send('{}\n'.format(stdin))
            finally:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, tty_prev)
        channel.close()
