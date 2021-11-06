import getpass
import sys
import threading
import time

import ipywidgets
import paramiko
from IPython.display import display
from paramiko import AuthenticationException, BadAuthenticationType, SSHException


class SSH(paramiko.SSHClient):

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.load_system_host_keys()
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.server = None
        if len(args) or len(kwargs):
            self.connect(*args, **kwargs)

    def __del__(self):
        self.close()

    def connect(self, server, username, password=None, *args, **kwargs):
        self.close()
        self.server = None
        super().connect(server, username=username, password=password, *args, **kwargs)
        self.server = server

    def exec_command(self, command, *args, **kwargs):
        block = kwargs.pop('block', True)
        verbose = kwargs.pop('verbose', True)
        if not isinstance(command, str):
            command = '\n'.join(command)
        _, stdout, stderr = super().exec_command(command, *args, **kwargs)
        if block:
            stdout.channel.recv_exit_status()
        stdouts = [x.strip('\n') for x in stdout]
        stderrs = [x.strip('\n') for x in stderr]
        if verbose:
            if stdouts:
                print('\n'.join(stdouts), file=sys.stdout, flush=True)
            if stderrs:
                print('\n'.join(stderrs), file=sys.stderr, flush=True)
        return stdouts, stderrs

    def invoke_shell(self, *args, **kwargs):
        channel = super().invoke_shell(*args, **kwargs)
        output = ipywidgets.Output()
        stdin = ipywidgets.widgets.Text(placeholder='Enter bash command')
        display(ipywidgets.VBox((output, stdin)))

        def writeall(channel_, output_):
            while True:
                stdout = paramiko.py3compat.u(channel_.recv(1024))
                if stdout:
                    output_.append_stdout(stdout)
        writer = threading.Thread(target=writeall, args=(channel, output))
        writer.start()

        def callback(widget):
            if widget.value in ('exit', 'quit', 'q'):
                writer.join(0)
                channel.close()
                stdin.close()
            else:
                channel.send(f'{widget.value}\n')
            if widget.value == 'clear':
                lastline = output.outputs[-1]['text'].splitlines()[-1]
                time.sleep(0.1)
                output.outputs = ()
                output.append_stdout(lastline)
            widget.value = ''
        stdin.on_submit(callback)
