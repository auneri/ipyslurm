# TODO(auneri1) Expand user in sftp magic, work with quotes.
# TODO(auneri1) Recursive option for sftp rm.
# TODO(auneri1) Tail length should be configurable in sbatch.

from __future__ import absolute_import, division, print_function

import datetime
import getpass
import importlib
import os
import platform
import stat
import sys
import time
import timeit

import paramiko
from IPython.core import magic
from IPython.display import clear_output
from six import print_ as print
from six.moves import input

from PythonTools import distributed, progress


def get(ftp, remote, local, resume=False, dryrun=False):
    try:
        if not resume or (os.stat(local)[stat.ST_MTIME] != ftp.stat(remote).st_mtime):
            raise IOError
    except IOError:
        if dryrun:
            print('get {} {}'.format(remote, local))
        else:
            ftp.get(remote, local)
            stats = ftp.stat(remote)
            os.utime(local, (stats.st_atime, stats.st_mtime))


def interact(channel):
    if platform.system() == 'Windows':
        import threading

        def writeall(channel_):
            while True:
                stdout = channel_.recv(256)
                if not stdout:
                    sys.stdout.flush()
                    break
                sys.stdout.write(stdout)
                sys.stdout.flush()
        writer = threading.Thread(target=writeall, args=(channel,))
        writer.start()
        while True:
            stdin = input()
            if stdin in ('exit', 'quit', 'q'):
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
                    if stdin in ('exit', 'quit', 'q'):
                        break
                    channel.send('{}\n'.format(stdin))
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, tty_prev)


def put(ftp, local, remote, resume=False, dryrun=False):
    try:
        if not resume or (os.stat(local)[stat.ST_MTIME] != ftp.stat(remote).st_mtime):
            raise IOError
    except IOError:
        if dryrun:
            print('put {} {}'.format(local, remote))
        else:
            ftp.put(local, remote)
            stats = os.stat(local)
            ftp.utime(remote, (stats.st_atime, stats.st_mtime))


def walk(ftp, remote):
    dirnames, filenames = [], []
    for f in ftp.listdir_attr(remote):
        if stat.S_ISDIR(f.st_mode):
            dirnames.append(f.filename)
        else:
            filenames.append(f.filename)
    yield remote, dirnames, filenames
    for dirname in dirnames:
        for x in walk(ftp, '{}/{}'.format(remote, dirname)):
            yield x


@magic.magics_class
class Slurm(magic.Magics):

    def __init__(self, *args, **kwargs):
        super(Slurm, self).__init__(*args, **kwargs)
        self._ssh = None
        self._ssh_data = None

    def __del__(self):
        self.slogout()
        super(Slurm, self).__del__()

    def __repr__(self):
        if self._ssh is not None:
            return 'Logged in to {}'.format(self._ssh.get_server())

    @magic.needs_local_scope
    @magic.cell_magic
    def sbash(self, line='', cell=None):
        if self._ssh is None:
            raise paramiko.AuthenticationException('Please login using %slogin')
        opts, _ = self.parse_options(line, 'p:t:so:se:', 'period=', 'timeout=', 'stdout=', 'stderr=')
        stdout = opts.get('so', None) or opts.get('stdout', None)
        stderr = opts.get('se', None) or opts.get('stderr', None)
        period = opts.get('p', None) or opts.get('period', None)
        timeout = opts.get('t', None) or opts.get('timeout', None)
        if period is not None:
            period = float(period)
        if timeout is not None:
            timeout = float(timeout)
        shebangs = [i for i, l in enumerate(cell.splitlines()) if l.startswith('#!')]
        if len(shebangs) == 0:
            command = '\n'.join(cell.splitlines())
        elif len(shebangs) == 1:
            cell = '\n'.join(l.replace('\\', '\\\\\\').replace('$', '\\$').replace('"', '\\"') for l in cell.splitlines() if not l.startswith('#SBATCH'))
            command = '\n'.join(cell.splitlines()[:shebangs[0]])
            script = '\n'.join(cell.splitlines()[shebangs[0]:])
            self._ssh.exec_command('mkdir -p ~/.magic'.format(script))
            self._ssh.exec_command('echo -e "{}" > ~/.magic/sbash'.format(script))
            self._ssh.exec_command('chmod +x ~/.magic/sbash')
            command = '\n'.join((command, '~/.magic/sbash'))
        else:
            raise NotImplementedError
        start = timeit.default_timer()
        try:
            while True:
                clear_output(wait=True)
                stdouts, stderrs = self._ssh.exec_command(command, verbose=stdout is None and stderr is None)
                elapsed = timeit.default_timer() - start
                if timeout is not None and elapsed > timeout:
                    print('\nsbash terminated after {:.1f} seconds'.format(elapsed))
                    break
                if period is not None:
                    time.sleep(period)
                else:
                    break
        except KeyboardInterrupt:
            pass
        else:
            if stdout is not None:
                self.shell.user_ns.update({stdout: stdouts})
            if stderr is not None:
                self.shell.user_ns.update({stderr: stderrs})

    @magic.cell_magic
    def sbatch(self, line='', cell=None):
        if self._ssh is None:
            raise paramiko.AuthenticationException('Please login using %slogin')
        line, wait = line.replace('--wait', ''), '--wait' in line
        line, tail = line.replace('--tail', ''), '--tail' in line
        line = ' '.join(l.replace('#SBATCH', '').strip() for l in cell.splitlines() if l.startswith('#SBATCH'))
        cell = '\n'.join(l.replace('\\', '\\\\\\').replace('$', '\\$').replace('"', '\\"') for l in cell.splitlines() if not l.startswith('#SBATCH'))
        shebangs = [i for i, l in enumerate(cell.splitlines()) if l.startswith('#!')]
        if len(shebangs) == 0:
            command = '\n'.join(cell.splitlines())
        elif len(shebangs) == 1:
            command = '\n'.join(cell.splitlines()[:shebangs[0]])
            script = '\n'.join(cell.splitlines()[shebangs[0]:])
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            self._ssh.exec_command('mkdir -p ~/.magic'.format(script))
            self._ssh.exec_command('echo -e "{}" > ~/.magic/sbatch_{}'.format(script, timestamp))
            self._ssh.exec_command('chmod +x ~/.magic/sbatch_{}'.format(timestamp))
            command = '\n'.join((command, '~/.magic/sbatch_{}'.format(timestamp)))
        else:
            raise NotImplementedError
        stdouts, _ = self._ssh.exec_command('sbatch {} --wrap="{}"'.format(line, command))
        if stdouts and stdouts[-1].startswith('Submitted batch job '):
            job = int(stdouts[-1].lstrip('Submitted batch job '))
        else:
            job = None
        if job is not None and (wait or tail):
            keys = 'JobId', 'JobName', 'JobState', 'SubmitTime', 'StartTime', 'RunTime'
            fill = max(len(i) for i in keys)
            try:
                while True:
                    stdouts, _ = self._ssh.exec_command('scontrol show jobid {}'.format(job), verbose=False)
                    details = dict(line.split('=', 1) for line in '\n'.join(stdouts).split())
                    clear_output(wait=True)
                    if tail and details['JobState'] in ('RUNNING', 'COMPLETING', 'COMPLETED'):
                        self._ssh.exec_command('tail --lines=10 {}'.format(details['StdOut']))
                    else:
                        for key in keys:
                            print('{1:>{0}}: {2}'.format(fill, key, details[key]))
                    if details['JobState'] not in ('PENDING', 'CONFIGURING', 'RUNNING', 'COMPLETING'):
                        break
            except KeyboardInterrupt:
                self._ssh.exec_command('scancel {}'.format(job))

    @magic.line_magic
    @magic.cell_magic
    def sftp(self, line='', cell=None):
        """Commands: cd, chmod, chown, get, lls, ln, lpwd, ls, mkdir, put, pwd, rename, rm, rmdir, symlink.

        See interactive commands section of http://man.openbsd.org/sftp for details.
        """
        if self._ssh is None:
            raise paramiko.AuthenticationException('Please login using %slogin')
        opts, _ = self.parse_options(line, 'vdi:', 'verbose', 'dryrun', 'instructions=')
        verbose = 'v' in opts or 'verbose' in opts
        dryrun = 'd' in opts or 'dryrun' in opts
        instructions = opts.get('i', '') or opts.get('instructions', '')
        lines = instructions.splitlines()
        if cell is not None:
            lines += cell.splitlines()
        ssh = self._ssh if self._ssh_data is None else self._ssh_data
        ftp = ssh.open_sftp()
        ftp.chdir(ssh.exec_command('pwd', verbose=False)[0][0])
        try:
            for line in progress.iterator(lines, show=verbose and instructions):
                argv = line.split()
                if not argv:
                    continue
                if argv[0].startswith('#'):
                    continue
                commands = {
                    'cd': 'chdir',
                    'chmod': 'chmod',
                    'chown': 'chown',
                    'get': 'get',
                    'lls': 'listdir',
                    'lmkdir': 'os.mkdir',
                    'ln': 'symlink',
                    'lpwd': 'getcwd',
                    'ls': 'listdir',
                    'mkdir': 'mkdir',
                    'put': 'put',
                    'pwd': 'getcwd',
                    'rename': 'rename',
                    'rm': 'remove',
                    'rmdir': 'rmdir',
                    'symlink': 'symlink'}
                if argv[0] in commands:
                    command = commands[argv[0]]
                    if argv[0] == 'get':
                        recurse, resume = False, False
                        for arg in list(argv):
                            if arg.startswith('-'):
                                recurse |= 'r' in arg
                                resume |= 'a' in arg
                                argv.remove(arg)
                        if len(argv) != 3:
                            raise ValueError('get [-drav] remote_file local_file')
                        local, remote = argv[2], argv[1]
                        if stat.S_ISDIR(ftp.stat(remote).st_mode):
                            if verbose:
                                pbar = progress.ProgressBar(sum(len(filenames) for i, (_, _, filenames) in enumerate(walk(ftp, remote)) if recurse or i == 0))
                            for dirpath, _, filenames in walk(ftp, remote):
                                root = local + os.path.sep.join(dirpath.replace(remote, '').split('/'))
                                try:
                                    os.mkdir(root)
                                except OSError:
                                    pass
                                for filename in filenames:
                                    get(ftp, '{}/{}'.format(dirpath, filename), os.path.join(root, filename), resume, dryrun)
                                    if verbose:
                                        pbar.increment()
                                if not recurse:
                                    break
                            if verbose:
                                pbar.done()
                        else:
                            get(ftp, remote, local, resume, dryrun)
                    elif argv[0] == 'put':
                        recurse, resume = False, False
                        for arg in list(argv):
                            if arg.startswith('-'):
                                recurse |= 'r' in arg
                                resume |= 'a' in arg
                                argv.remove(arg)
                        if len(argv) != 3:
                            raise ValueError('put [-drav] local_file remote_file')
                        local, remote = argv[1], argv[2]
                        if os.path.isdir(local):
                            if verbose:
                                pbar = progress.ProgressBar(sum(len(filenames) for i, (_, _, filenames) in enumerate(os.walk(local)) if recurse or i == 0))
                            for dirpath, _, filenames in os.walk(local):
                                root = remote + '/'.join(dirpath.replace(local, '').split(os.path.sep))
                                try:
                                    ftp.mkdir(root)
                                except OSError:
                                    pass
                                for filename in filenames:
                                    put(ftp, os.path.join(dirpath, filename), '{}/{}'.format(root, filename), resume, dryrun)
                                    if verbose:
                                        pbar.increment()
                                if not recurse:
                                    break
                            if verbose:
                                pbar.done()
                        else:
                            put(ftp, local, remote, resume, dryrun)
                    elif argv[0] in ('lls', 'lpwd'):
                        if dryrun:
                            print(' '.join(argv))
                        else:
                            output = getattr(ftp, command)(*argv[1:])
                    elif argv[0] == 'lmkdir':
                        if dryrun:
                            print(' '.join(argv))
                        else:
                            getattr(importlib.import_module(command.rsplit('.', 1)[0]), command.rsplit('.', 1)[1])(*argv[1:])
                    else:
                        if dryrun:
                            print(' '.join(argv))
                        else:
                            output = getattr(ftp, command)(*argv[1:])
                    if command == 'getcwd' and not dryrun:
                        print(output)
                    elif command == 'listdir' and not dryrun:
                        print('\n'.join(sorted(output)))
                else:
                    raise SyntaxError('Command "{}" is not supported'.format(argv[0]))
        except KeyboardInterrupt:
            pass
        finally:
            ftp.close()

    @magic.line_magic
    def sinteract(self, line=''):
        channel = self._ssh.invoke_shell()
        interact(channel)
        channel.close()

    @magic.line_magic
    def slogin(self, line=''):
        opts, _ = self.parse_options(line, 's:u:p:d:', 'server=', 'username=', 'password=', 'data-server=')
        server = opts.get('s', None) or opts.get('server', None)
        username = opts.get('u', None) or opts.get('username', None)
        password = opts.get('p', None) or opts.get('password', None)
        server_data = opts.get('d', None) or opts.get('data-server', None)
        if server is None:
            server = input('Server: ')
        if username is None:
            username = getpass.getuser()
        if server_data is not None:
            try:
                print('Logging in to {}@{}'.format(username, server_data))
                self._ssh_data = distributed.SSHClient()
                self._ssh_data.connect(server_data, username, password)
                self._ssh_data.get_transport().set_keepalive(30)
                print('Please wait for a new verification code before logging in to {}!'.format(server))
            except:  # noqa: E722
                self._ssh_data = None
                raise
        try:
            print('Logging in to {}@{}'.format(username, server))
            self._ssh = distributed.SSHClient()
            self._ssh.connect(server, username, password)
            self._ssh.get_transport().set_keepalive(30)
        except:  # noqa: E722
            self._ssh = None
            raise
        return self

    @magic.line_magic
    def slogout(self, line=''):
        if self._ssh is not None:
            print('Logging out of {}'.format(self._ssh.get_server()))
        self._ssh = None
        if self._ssh_data is not None:
            print('Logging out of {}'.format(self._ssh_data.get_server()))
        self._ssh_data = None


def load_ipython_extension(ipython):
    ipython.register_magics(Slurm)
