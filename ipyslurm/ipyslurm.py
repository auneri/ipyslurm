import datetime
import importlib
import os
import stat
import sys
import time
import timeit
import warnings

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
        stdouts, _ = ssh.exec_command('readlink -f {}'.format(path), verbose=False)
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
    def sbatch(self, line, cell):
        """Submit a batch script to Slurm."""
        args = magic_arguments.parse_argstring(self.sbatch, line)
        job = self._slurm.batch(cell.splitlines(), args.args)
        if args.wait or args.tail is not None:
            keys = 'JobName', 'JobId', 'JobState', 'Reason', 'SubmitTime', 'StartTime', 'RunTime'
            keys_maxlen = max(len(i) for i in keys)
            try:
                while True:
                    stdouts, _ = self._slurm._ssh.exec_command('scontrol show jobid {}'.format(job), verbose=False)
                    details = dict(line.split('=', 1) for line in '\n'.join(stdouts).split())
                    clear_output(wait=True)
                    if args.tail is not None and details['JobState'] in ['RUNNING', 'COMPLETING', 'COMPLETED', 'FAILED']:
                        self._slurm._ssh.exec_command('tail --lines={} {}'.format(args.tail, details['StdOut']))
                    else:
                        print('\n'.join('{1:>{0}}: {2}'.format(keys_maxlen, key, details[key]) for key in keys))
                    if details['JobState'] not in ['PENDING', 'CONFIGURING', 'RUNNING', 'COMPLETING']:
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
            'ls': 'listdir',
            'mkdir': 'mkdir',
            'put': 'put',
            'pwd': 'getcwd',
            'rename': 'rename',
            'rm': 'remove',
            'rmdir': 'rmdir',
            'symlink': 'symlink'}
        args = magic_arguments.parse_argstring(self.sftp, line)
        lines = [line for line in cell.splitlines() if line.strip() and not line.lstrip().startswith('#')]
        with self._slurm.ftp() as (ssh, ftp), warnings.catch_warnings():
            warnings.filterwarnings(action='ignore', module='.*paramiko.*')
            pbars = [ProgressBar(hide=args.quiet or not any(x.startswith(y) for y in ('get', 'put'))) for x in lines]
            for line, pbar in zip(lines, pbars):
                argv = line.split()
                command = commands.get(argv[0])
                if command is None:
                    raise SyntaxError('"{}" is not supported'.format(argv[0]))
                if argv[0] == 'cd':
                    if len(argv) != 2:
                        raise ValueError('cd remote_directory')
                    output = getattr(ftp, command)(normalize(argv[1], ssh, ftp))
                elif argv[0] == 'get':
                    recurse, resume = False, False
                    for arg in list(argv):
                        if arg.startswith('-'):
                            recurse |= 'r' in arg
                            resume |= 'a' in arg
                            argv.remove(arg)
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
                        pbar.close()
                    else:
                        get(ftp, remote, local, resume)
                elif argv[0] == 'put':
                    recurse, resume = False, False
                    for arg in list(argv):
                        if arg.startswith('-'):
                            recurse |= 'r' in arg
                            resume |= 'a' in arg
                            argv.remove(arg)
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
                        pbar.close()
                    else:
                        put(ftp, local, remote, resume)
                elif argv[0] == 'lcd':
                    if len(argv) != 2:
                        raise ValueError('lcd local_directory')
                    output = getattr(importlib.import_module(command.rsplit('.', 1)[0]), command.rsplit('.', 1)[1])(normalize(argv[1]))
                elif argv[0] in ['lls', 'lmkdir', 'lpwd']:
                    output = getattr(importlib.import_module(command.rsplit('.', 1)[0]), command.rsplit('.', 1)[1])(*argv[1:])
                else:
                    output = getattr(ftp, command)(*argv[1:])
                if argv[0] in ['pwd', 'lpwd']:
                    print(output)
                elif argv[0] in ['ls', 'lls']:
                    print('\n'.join(output))

    @magic.line_magic
    def sinteract(self, line):
        self._slurm.interact()

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('server', help='Address of server')
    @magic_arguments.argument('--username', help='Username, interactively requested if not provided')
    @magic_arguments.argument('--password', help='Password, interactively requested if not provided')
    @magic_arguments.argument('--data-server', metavar='ADDRESS', help='Address of server for data transfers')
    @magic.line_magic
    def slogin(self, line):
        """Login to server."""
        args = magic_arguments.parse_argstring(self.slogin, line)
        with warnings.catch_warnings():
            warnings.filterwarnings(action='ignore', module='.*paramiko.*')
            self._slurm.login(args.server, args.username, args.password, args.data_server)
        return self._slurm

    @magic.line_magic
    def slogout(self, line):
        """Logout of server."""
        self._slurm.logout()

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('filepath', help='Path of file')
    @magic_arguments.argument('--append', action='store_true', help='Append contents of the cell to an existing file')
    @magic.cell_magic
    def swritefile(self, line, cell):
        args = magic_arguments.parse_argstring(self.swritefile, line)
        lines = ['cat << \\EOF {} {}'.format('>>' if args.append else '>', args.filepath)] + cell.splitlines() + ['EOF']
        for _ in self._slurm.bash(lines, verbose=True):
            break
