import getpass
import logging
import threading
import time

import ipywidgets
import paramiko
from IPython.display import display


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

    def close(self):
        super().close()
        self.server = None

    def connect(self, server, username, password=None, keepalive=30, **kwargs):
        self.close()
        try:
            super().connect(server, username=username, **kwargs)
        except paramiko.AuthenticationException:
            try:
                def handler(title, instructions, prompt_list):
                    if title:
                        print(title.strip())
                    if instructions:
                        print(instructions.strip())
                    responses = []
                    for prompt, show_input in prompt_list:
                        if password is not None and prompt.strip().lower() == 'password:':
                            responses.append(password)
                        elif show_input:
                            responses.append(input(prompt.strip()))
                        else:
                            responses.append(getpass.getpass(prompt.strip()))
                    return responses
                self._transport.auth_interactive_dumb(username, handler=handler)
            except paramiko.AuthenticationException:
                if password is None:
                    password = getpass.getpass('Password:')
                self._transport.auth_password(username, password)
        self._transport.set_keepalive(keepalive)
        self.server = server

    def exec_command(self, command, block=True, error=True, **kwargs):
        if not isinstance(command, str):
            command = '\n'.join(command)
        if command:
            logging.getLogger('ipyslurm.ssh').debug(f'stdin: "{command}"')
        _, stdout, stderr = super().exec_command(command, **kwargs)
        status = stdout.channel.recv_exit_status() if block else -1
        stdouts = [x.strip('\n') for x in stdout]
        stderrs = [x.strip('\n') for x in stderr]
        if error and status > 0:
            message = f'Command returned with exit code {status}:'
            message += f'\nstdin: "{command}"'
            if stdouts:
                message += '\nstdout: "{}"'.format('\n'.join(stdouts))
            if stderrs:
                message += '\nstderr: "{}"'.format('\n'.join(stderrs))
            raise RuntimeError(message)
        for stdout in stdouts:
            logging.getLogger('ipyslurm.ssh').debug(f'stdout: "{stdout}"')
        for stderr in stderrs:
            logging.getLogger('ipyslurm.ssh').debug(f'stderr: "{stderr}"')
        return stdouts

    def invoke_shell(self, **kwargs):
        channel = super().invoke_shell(**kwargs)
        output = ipywidgets.Output()
        stdin = ipywidgets.widgets.Text(placeholder='Enter shell command')
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
