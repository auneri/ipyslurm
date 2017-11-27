#!/usr/bin/env python

from __future__ import absolute_import, division, print_function

import getpass
import sys

import paramiko
from six import print_ as print


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
        except (paramiko.AuthenticationException, paramiko.SSHException):
            def handler(title, instructions, prompt_list):
                if title:
                    print(title.strip())
                if instructions:
                    print(instructions.strip())
                return [show_input and input(prompt.strip()) or getpass.getpass(prompt.strip()) for prompt, show_input in prompt_list]
            self.get_transport().auth_interactive_dumb(username=username, handler=handler)
        self._server = server

    def exec_command(self, *args, **kwargs):
        verbose = kwargs.pop('verbose', True)
        _, stdout, stderr = super(SSHClient, self).exec_command(*args, **kwargs)
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

    def get_server(self):
        return self._server
