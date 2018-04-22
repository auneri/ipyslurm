#!/usr/bin/env python

from __future__ import absolute_import, division, print_function

import getpass
import platform
import sys

import paramiko
from paramiko import AuthenticationException
from six import print_ as print  # noqa: A001
from six import string_types


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
