#!/usr/bin/env python

from __future__ import absolute_import, division, print_function

import datetime
import getpass
import importlib
import os
import stat
import sys
import time
import timeit

from IPython.core import magic
from IPython.display import clear_output
from six import print_ as print  # noqa: A001
from six.moves import input
from tqdm import tqdm_notebook

from . import client


def get(ftp, remote, local, resume=False, dryrun=False):
    try:
        if not resume:
            raise IOError
        remote_timestamp = datetime.datetime.fromtimestamp(ftp.stat(remote).st_mtime)
        local_timestamp = datetime.datetime.fromtimestamp(os.stat(local)[stat.ST_MTIME])
        if remote_timestamp > local_timestamp:
            raise IOError
    except IOError:
        if dryrun:
            print('get {} {}'.format(remote, local))
        else:
            ftp.get(remote, local)
            stats = ftp.stat(remote)
            os.utime(local, (stats.st_atime, stats.st_mtime))


def normalize(path, ssh=None):
    if path.startswith('"'):
        path = path.replace('"', '')
    elif path.startswith("'"):
        path = path.replace("'", '')
    if ssh is None:
        return os.path.abspath(os.path.expanduser(path))
    else:
        try:
            return ssh.exec_command('readlink -f {}'.format(path), verbose=False)[0][0]
        except IndexError:
            raise OSError('Failed to find {}'.format(path))


def put(ftp, local, remote, resume=False, dryrun=False):
    try:
        if not resume:
            raise IOError
        local_timestamp = datetime.datetime.fromtimestamp(os.stat(local)[stat.ST_MTIME])
        remote_timestamp = datetime.datetime.fromtimestamp(ftp.stat(remote).st_mtime)
        if local_timestamp > remote_timestamp:
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
class IPySlurm(magic.Magics):

    def __init__(self, *args, **kwargs):
        super(IPySlurm, self).__init__(*args, **kwargs)
        self._slurm = client.Slurm()

    @magic.needs_local_scope
    @magic.cell_magic
    def sbash(self, line='', cell=None):
        opts, _ = self.parse_options(line, 'p:t:so:se:', 'period=', 'timeout=', 'stdout=', 'stderr=')
        stdout = opts.get('so', None) or opts.get('stdout', None)
        stderr = opts.get('se', None) or opts.get('stderr', None)
        period = opts.get('p', None) or opts.get('period', None)
        timeout = opts.get('t', None) or opts.get('timeout', None)
        if period is not None:
            period = float(period)
        if timeout is not None:
            timeout = float(timeout)
        start = timeit.default_timer()
        for stdouts, stderrs in self._slurm.bash(cell.splitlines(), verbose=stdout is None and stderr is None):
            elapsed = timeit.default_timer() - start
            if timeout is not None and elapsed > timeout:
                print('\nsbash terminated after {:.1f} seconds'.format(elapsed))
            elif period is not None:
                sys.stdout.flush()
                sys.stderr.flush()
                time.sleep(period)
                clear_output(wait=True)
                continue
            break
        if stdout is not None:
            self.shell.user_ns.update({stdout: stdouts})
        if stderr is not None:
            self.shell.user_ns.update({stderr: stderrs})

    @magic.cell_magic
    def sbatch(self, line='', cell=None):
        opts, _ = self.parse_options(line, 'wt:a:', 'wait', 'tail=', 'args=')
        wait = 'w' in opts or 'wait' in opts
        tail = opts.get('t', None) or opts.get('tail', None)
        args = opts.get('a', None) or opts.get('args', None)
        if tail is not None:
            tail = int(tail)
        job = self._slurm.batch(cell.splitlines(), args)
        if wait or tail is not None:
            keys = 'JobName', 'JobId', 'JobState', 'SubmitTime', 'StartTime', 'RunTime'
            fill = max(len(i) for i in keys)
            try:
                while True:
                    stdouts, _ = self._slurm._ssh.exec_command('scontrol show jobid {}'.format(job), verbose=False)
                    details = dict(line.split('=', 1) for line in '\n'.join(stdouts).split())
                    clear_output(wait=True)
                    if tail is not None and details['JobState'] in ['RUNNING', 'COMPLETING', 'COMPLETED', 'FAILED']:
                        self._slurm._ssh.exec_command('tail --lines={} {}'.format(tail, details['StdOut']))
                    else:
                        print('\n'.join('{1:>{0}}: {2}'.format(fill, key, details[key]) for key in keys))
                    if details['JobState'] not in ['PENDING', 'CONFIGURING', 'RUNNING', 'COMPLETING']:
                        break
            except KeyboardInterrupt:
                self._slurm._ssh.exec_command('scancel {}'.format(job))

    @magic.cell_magic
    def sftp(self, line='', cell=None):
        """Commands: cd, chmod, chown, get, lls, ln, lpwd, ls, mkdir, put, pwd, rename, rm, rmdir, symlink.

        See interactive commands section of http://man.openbsd.org/sftp for details.
        """
        commands = {
            'cd': 'chdir',
            'chmod': 'chmod',
            'chown': 'chown',
            'get': 'get',
            'lls': 'os.listdir',
            'lmkdir': 'os.mkdir',
            'ln': 'symlink',
            'lpwd': 'os.getcwd',
            'ls': 'listdir',
            'mkdir': 'mkdir',
            'put': 'put',
            'pwd': 'getcwd',
            'rename': 'rename',
            'rm': 'remove',
            'rmdir': 'rmdir',
            'symlink': 'symlink'}
        opts, _ = self.parse_options(line, 'vdi:', 'verbose', 'dryrun', 'instructions=')
        verbose = 'v' in opts or 'verbose' in opts
        dryrun = 'd' in opts or 'dryrun' in opts
        instructions = opts.get('i', '') or opts.get('instructions', '')
        lines = instructions.splitlines()
        if cell is not None:
            lines += cell.splitlines()
        lines = [line for line in lines if line.strip() and not line.lstrip().startswith('#')]
        with self._slurm.ftp() as (ssh, ftp):
            for line in tqdm_notebook(lines, desc='Progress', unit='op', disable=not verbose or len(lines) < 2):
                argv = line.split()
                command = commands.get(argv[0])
                if command is None:
                    raise SyntaxError('"{}" is not supported'.format(argv[0]))
                if argv[0] == 'get':
                    recurse, resume = False, False
                    for arg in list(argv):
                        if arg.startswith('-'):
                            recurse |= 'r' in arg
                            resume |= 'a' in arg
                            argv.remove(arg)
                    if len(argv) != 3:
                        raise ValueError('get [-ra] remote_file local_file')
                    local, remote = normalize(argv[2]), normalize(argv[1], ssh)
                    if stat.S_ISDIR(ftp.stat(remote).st_mode):
                        pbar = tqdm_notebook(total=sum(len(filenames) for i, (_, _, filenames) in enumerate(walk(ftp, remote)) if recurse or i == 0), unit='op', disable=not verbose)
                        for dirpath, _, filenames in walk(ftp, remote):
                            root = local + os.path.sep.join(dirpath.replace(remote, '').split('/'))
                            try:
                                os.mkdir(root)
                            except OSError:
                                pass
                            for filename in filenames:
                                get(ftp, '{}/{}'.format(dirpath, filename), os.path.join(root, filename), resume, dryrun)
                                pbar.update()
                            if not recurse:
                                break
                        pbar.close()
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
                        raise ValueError('put [-ra] local_file remote_file')
                    local, remote = normalize(argv[1]), normalize(argv[2], ssh)
                    if os.path.isdir(local):
                        pbar = tqdm_notebook(total=sum(len(filenames) for i, (_, _, filenames) in enumerate(os.walk(local)) if recurse or i == 0), unit='op', disable=not verbose)
                        for dirpath, _, filenames in os.walk(local):
                            root = remote + '/'.join(dirpath.replace(local, '').split(os.path.sep))
                            try:
                                ftp.mkdir(root)
                            except OSError:
                                pass
                            for filename in filenames:
                                put(ftp, os.path.join(dirpath, filename), '{}/{}'.format(root, filename), resume, dryrun)
                                pbar.update()
                            if not recurse:
                                break
                        pbar.close()
                    else:
                        put(ftp, local, remote, resume, dryrun)
                elif argv[0] in ['lls', 'lmkdir', 'lpwd']:
                    if dryrun:
                        print(' '.join(argv))
                    else:
                        output = getattr(importlib.import_module(command.rsplit('.', 1)[0]), command.rsplit('.', 1)[1])(*argv[1:])
                else:
                    if dryrun:
                        print(' '.join(argv))
                    else:
                        output = getattr(ftp, command)(*argv[1:])
                if argv[0] in ['pwd', 'lpwd'] and not dryrun:
                    print(output)
                elif argv[0] in ['ls', 'lls'] and not dryrun:
                    print('\n'.join(output))

    @magic.line_magic
    def sinteract(self, line=''):
        self._slurm.interact()

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
        self._slurm.login(server, username, password, server_data)
        return self._slurm

    @magic.line_magic
    def slogout(self, line=''):
        self._slurm.logout()
