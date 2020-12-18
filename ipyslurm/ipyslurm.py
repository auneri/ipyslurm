import datetime
import importlib
import os
import re
import shlex
import stat
import sys
import time
import timeit

from IPython.core import magic, magic_arguments
from IPython.display import clear_output

from .client import Slurm
from .progress import ProgressBar


def get(ftp, remote, local, resume=False):
    try:
        if not resume:
            raise IOError
        remote_timestamp = datetime.datetime.fromtimestamp(ftp.stat(remote).st_mtime)
        local_timestamp = datetime.datetime.fromtimestamp(os.stat(local)[stat.ST_MTIME])
        if remote_timestamp > local_timestamp:
            raise IOError
    except IOError:
        ftp.get(remote, local)
        stats = ftp.stat(remote)
        os.utime(local, (stats.st_atime, stats.st_mtime))


def normalize(path, ssh=None, ftp=None):
    if path.startswith('"'):
        path = path.replace('"', '')
    elif path.startswith("'"):
        path = path.replace("'", '')
    if None in (ssh, ftp):
        return os.path.abspath(os.path.expanduser(path))
    else:
        cwd = ftp.getcwd()
        if cwd is not None:
            path = '{}/{}'.format(cwd, path)
        stdouts, _ = ssh.exec_command('readlink -f "{}"'.format(path), verbose=False)
        if len(stdouts) != 1:
            raise OSError('Failed to find {}'.format(path))
        return stdouts[0]


def put(ftp, local, remote, resume=False):
    try:
        if not resume:
            raise IOError
        local_timestamp = datetime.datetime.fromtimestamp(os.stat(local)[stat.ST_MTIME])
        remote_timestamp = datetime.datetime.fromtimestamp(ftp.stat(remote).st_mtime)
        if local_timestamp > remote_timestamp:
            raise IOError
    except IOError:
        ftp.put(local, remote)
        stats = os.stat(local)
        ftp.utime(remote, (stats.st_atime, stats.st_mtime))


def sort_key_natural(s, _nsre=re.compile('([0-9]+)')):
    """Adapted from http://blog.codinghorror.com/sorting-for-humans-natural-sort-order."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(_nsre, str(s))]


def walk(ftp, top, topdown=True, followlinks=False):
    dirnames, filenames = [], []
    try:
        attrs = ftp.listdir_attr(top)
    except FileNotFoundError:
        raise FileNotFoundError('Failed to list contents of "{}"'.format(top))
    for attr in attrs:
        if stat.S_ISDIR(attr.st_mode):
            dirnames.append(attr)
        else:
            filenames.append(attr)
    if topdown:
        yield top, [x.filename for x in dirnames], [x.filename for x in filenames]
    for attr in dirnames:
        dirpath = '{}/{}'.format(top, attr.filename)
        if followlinks or not stat.S_ISLNK(attr.st_mode):
            for x in walk(ftp, dirpath, topdown, followlinks):
                yield x
    if not topdown:
        yield top, [x.filename for x in dirnames], [x.filename for x in filenames]


@magic.magics_class
class IPySlurm(magic.Magics):

    def __init__(self, *args, **kwargs):
        super(IPySlurm, self).__init__(*args, **kwargs)
        self._slurm = Slurm()

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('--period', type=float, metavar='SECONDS', help='Repeat execution with a given periodicity')
    @magic_arguments.argument('--timeout', type=float, metavar='SECONDS', help='Timeout for when used with --period')
    @magic_arguments.argument('--stdout', metavar='LIST', help='Variable to store stdout')
    @magic_arguments.argument('--stderr', metavar='LIST', help='Variable to store stderr')
    @magic.cell_magic
    @magic.needs_local_scope
    def sbash(self, line, cell, local_ns):
        """Execute a bash script on server."""
        args = magic_arguments.parse_argstring(self.sbash, line)
        start = timeit.default_timer()
        try:
            for stdouts, stderrs in self._slurm.bash(cell.splitlines(), verbose=args.stdout is None and args.stderr is None):
                elapsed = timeit.default_timer() - start
                if args.timeout is not None and elapsed > args.timeout:
                    print('\nsbash terminated after {:.1f} seconds'.format(elapsed))
                elif args.period is not None:
                    time.sleep(args.period)
                    clear_output(wait=True)
                    continue
                break
        except KeyboardInterrupt:
            pass
        if args.stdout is not None:
            local_ns.update({args.stdout: stdouts})
        if args.stderr is not None:
            local_ns.update({args.stderr: stderrs})

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('--wait', action='store_true', help='Block until execution is complete')
    @magic_arguments.argument('--tail', type=int, metavar='N', help='Block and print last N lines of the log')
    @magic_arguments.argument('--args', nargs='*', metavar='ARG', help='Additional arguments to sbatch')
    @magic.cell_magic
    @magic.line_magic
    def sbatch(self, line, cell=''):
        """Submit a batch script to Slurm."""
        args = magic_arguments.parse_argstring(self.sbatch, line)
        job = self._slurm.batch(cell.splitlines(), args.args)
        if args.wait or args.tail is not None:
            keys = 'JobName', 'JobId', 'JobState', 'Reason', 'SubmitTime', 'StartTime', 'RunTime'
            try:
                while True:
                    stdouts, _ = self._slurm._ssh.exec_command('scontrol show jobid {}'.format(job), verbose=False)
                    details = dict(x.split('=', 1) for x in '\n'.join(stdouts).split())
                    clear_output(wait=True)
                    if args.tail is not None and details['JobState'] in ('RUNNING', 'COMPLETING', 'COMPLETED', 'FAILED'):
                        self._slurm._ssh.exec_command('tail --lines={} {}'.format(args.tail, details['StdOut']))
                    else:
                        print('\n'.join('{1:>{0}}: {2}'.format(len(max(keys, key=len)), x, details[x]) for x in keys))
                    if details['JobState'] not in ('PENDING', 'CONFIGURING', 'RUNNING', 'COMPLETING'):
                        break
            except KeyboardInterrupt:
                self._slurm._ssh.exec_command('scancel {}'.format(job))
                print('Canceling job {}'.format(job), file=sys.stderr)

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('--quiet', action='store_true', help='Disable progress bar')
    @magic.cell_magic
    def sftp(self, line, cell):
        """File transfer over secure shell.

        Supported commands: cd, chmod, chown, get, lcd, lls, lmkdir, ln, lpwd, ls, mkdir, put, pwd, rename, rm, rmdir, symlink.
        See interactive commands section of http://man.openbsd.org/sftp for details.
        """
        commands = {
            'cd': 'chdir',
            'chmod': 'chmod',
            'chown': 'chown',
            'get': 'get',
            'lcd': 'os.chdir',
            'lls': 'os.listdir',
            'lmkdir': 'os.mkdir',
            'ln': 'symlink',
            'lpwd': 'os.getcwd',
            'lrm': 'os.remove',
            'lrmdir': 'os.rmdir',
            'ls': 'listdir',
            'mkdir': 'mkdir',
            'put': 'put',
            'pwd': 'getcwd',
            'rename': 'rename',
            'rm': 'remove',
            'rmdir': 'rmdir',
            'symlink': 'symlink'}
        args = magic_arguments.parse_argstring(self.sftp, line)
        lines = [x for x in cell.splitlines() if x.strip() and not x.lstrip().startswith('#')]
        with self._slurm.ftp() as (ssh, ftp):
            pbars = [ProgressBar(hide=args.quiet or not any(x.startswith(y) for y in ('get', 'put', 'rm'))) for x in lines]
            for line, pbar in zip(lines, pbars):
                argv = shlex.split(line, posix=False)
                command = commands.get(argv[0])
                if command is None:
                    raise SyntaxError('"{}" is not supported'.format(argv[0]))
                if argv[0] == 'cd':
                    if len(argv) != 2:
                        raise ValueError('cd remote_directory')
                    output = getattr(ftp, command)(normalize(argv[1], ssh, ftp))
                elif argv[0] == 'get':
                    recurse = bool([x for x in argv if x.startswith('-') and 'r' in x])
                    resume = bool([x for x in argv if x.startswith('-') and 'a' in x])
                    argv = [x for x in argv if not x.startswith('-')]
                    if len(argv) == 2:
                        argv.append(argv[-1])
                    elif len(argv) != 3:
                        raise ValueError('get [-ra] remote_file [local_file]')
                    local, remote = normalize(argv[2]), normalize(argv[1], ssh, ftp)
                    if stat.S_ISDIR(ftp.stat(remote).st_mode):
                        pbar.reset(sum(len(filenames) for i, (_, _, filenames) in enumerate(walk(ftp, remote)) if recurse or i == 0))
                        for dirpath, _, filenames in walk(ftp, remote):
                            root = local + os.path.sep.join(dirpath.replace(remote, '').split('/'))
                            try:
                                os.mkdir(root)
                            except OSError:
                                pass
                            for filename in filenames:
                                get(ftp, '{}/{}'.format(dirpath, filename), os.path.join(root, filename), resume)
                                pbar.update()
                            if not recurse:
                                break
                        pbar.close(clear=len(pbar) == 0)
                    else:
                        get(ftp, remote, local, resume)
                        pbar.close(clear=True)
                elif argv[0] == 'put':
                    recurse = bool([x for x in argv if x.startswith('-') and 'r' in x])
                    resume = bool([x for x in argv if x.startswith('-') and 'a' in x])
                    argv = [x for x in argv if not x.startswith('-')]
                    if len(argv) == 2:
                        argv.append(argv[-1])
                    elif len(argv) != 3:
                        raise ValueError('put [-ra] local_file [remote_file]')
                    local, remote = normalize(argv[1]), normalize(argv[2], ssh, ftp)
                    if os.path.isdir(local):
                        pbar.reset(sum(len(filenames) for i, (_, _, filenames) in enumerate(os.walk(local)) if recurse or i == 0))
                        for dirpath, _, filenames in os.walk(local):
                            root = remote + '/'.join(dirpath.replace(local, '').split(os.path.sep))
                            try:
                                ftp.mkdir(root)
                            except OSError:
                                pass
                            for filename in filenames:
                                put(ftp, os.path.join(dirpath, filename), '{}/{}'.format(root, filename), resume)
                                pbar.update()
                            if not recurse:
                                break
                        pbar.close(clear=len(pbar) == 0)
                    else:
                        put(ftp, local, remote, resume)
                        pbar.close(clear=True)
                elif argv[0] == 'lcd':
                    if len(argv) != 2:
                        raise ValueError('lcd local_directory')
                    output = getattr(importlib.import_module(command.rsplit('.', 1)[0]), command.rsplit('.', 1)[1])(normalize(argv[1]))
                elif argv[0] in ('lls', 'lmkdir', 'lpwd', 'lrmdir'):
                    output = getattr(importlib.import_module(command.rsplit('.', 1)[0]), command.rsplit('.', 1)[1])(*argv[1:])
                elif argv[0] == 'lrm':
                    recurse = bool([x for x in argv if x.startswith('-') and 'r' in x])
                    argv = [x for x in argv if not x.startswith('-')]
                    if len(argv) != 2:
                        raise ValueError('lrm [-r] local_file')
                    local = normalize(argv[1])
                    if recurse and os.path.isdir(local):
                        pbar.reset(sum(len(filenames) for i, (_, _, filenames) in enumerate(os.walk(local, topdown=False))), style='danger')
                        for dirpath, dirnames, filenames in os.walk(local, topdown=False):
                            for filename in filenames:
                                os.remove(os.path.join(dirpath, filename))
                                pbar.update()
                            for dirname in dirnames:
                                os.rmdir(os.path.join(dirpath, dirname))
                        os.rmdir(local)
                        pbar.close(clear=len(pbar) == 0)
                    else:
                        os.remove(local)
                        pbar.close(clear=True)
                elif argv[0] == 'ls':
                    if len(argv) != 2:
                        raise ValueError('ls remote_directory')
                    output = getattr(ftp, command)(normalize(argv[1], ssh, ftp))
                elif argv[0] == 'mkdir':
                    if len(argv) != 2:
                        raise ValueError('mkdir remote_directory')
                    output = getattr(ftp, command)(normalize(argv[1], ssh, ftp))
                elif argv[0] == 'rm':
                    recurse = bool([x for x in argv if x.startswith('-') and 'r' in x])
                    argv = [x for x in argv if not x.startswith('-')]
                    if len(argv) != 2:
                        raise ValueError('rm [-r] remote_file')
                    remote = normalize(argv[1], ssh, ftp)
                    if recurse and stat.S_ISDIR(ftp.stat(remote).st_mode):
                        pbar.reset(sum(len(filenames) for i, (_, _, filenames) in enumerate(walk(ftp, remote, topdown=False))), style='danger')
                        for dirpath, dirnames, filenames in walk(ftp, remote, topdown=False):
                            for filename in filenames:
                                ftp.remove('{}/{}'.format(dirpath, filename))
                                pbar.update()
                            for dirname in dirnames:
                                ftp.rmdir('{}/{}'.format(dirpath, dirname))
                        ftp.rmdir(remote)
                        pbar.close(clear=len(pbar) == 0)
                    else:
                        ftp.remove(remote)
                        pbar.close(clear=True)
                elif argv[0] == 'rmdir':
                    if len(argv) != 2:
                        raise ValueError('rmdir remote_directory')
                    output = getattr(ftp, command)(normalize(argv[1], ssh, ftp))
                else:  # 'chmod', 'chown', 'ln', 'pwd', 'rename', 'symlink'
                    output = getattr(ftp, command)(*argv[1:])
                if argv[0] in ('pwd', 'lpwd'):
                    print(output)
                elif argv[0] in ('ls', 'lls'):
                    print('\n'.join(sorted(output, key=sort_key_natural)))

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('server', help='Address of server')
    @magic_arguments.argument('--username', help='Username, interactively requested if not provided')
    @magic_arguments.argument('--password', help='Password, interactively requested if not provided')
    @magic_arguments.argument('--data-server', metavar='ADDRESS', help='Address of server for data transfers')
    @magic.line_magic
    def slogin(self, line):
        """Login to server."""
        args = magic_arguments.parse_argstring(self.slogin, line)
        self._slurm.login(args.server, args.username, args.password, args.data_server)
        return self._slurm

    @magic.line_magic
    def slogout(self, line):
        """Logout of server."""
        self._slurm.logout()

    @magic.line_magic
    def sshell(self, line):
        self._slurm.shell()

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('filepath', help='Path of file')
    @magic_arguments.argument('--append', action='store_true', help='Append contents of the cell to an existing file')
    @magic.cell_magic
    def swritefile(self, line, cell):
        args = magic_arguments.parse_argstring(self.swritefile, line)
        lines = ['cat << \\EOF {} {}'.format('>>' if args.append else '>', args.filepath)] + cell.splitlines() + ['EOF']
        for _ in self._slurm.bash(lines, verbose=True):
            break
