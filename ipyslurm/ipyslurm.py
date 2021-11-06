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

from .slurm import Slurm


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
            for stdouts, stderrs in self._slurm.script(cell.splitlines(), verbose=args.stdout is None and args.stderr is None):
                elapsed = timeit.default_timer() - start
                if args.timeout is not None and elapsed > args.timeout:
                    print(f'\nsbash terminated after {elapsed:.1f} seconds')
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
        job = self._slurm.sbatch(cell.splitlines(), args.args)
        if args.wait or args.tail is not None:
            keys = 'JobName', 'JobId', 'JobState', 'Reason', 'SubmitTime', 'StartTime', 'RunTime'
            try:
                while True:
                    stdouts, _ = self._slurm._ssh.exec_command(f'scontrol show jobid {job}', verbose=False)
                    details = dict(x.split('=', 1) for x in '\n'.join(stdouts).split())
                    clear_output(wait=True)
                    if args.tail is not None and details['JobState'] in ('RUNNING', 'COMPLETING', 'COMPLETED', 'FAILED'):
                        self._slurm._ssh.exec_command(f'tail --lines={args.tail} {details["StdOut"]}')
                    else:
                        print('\n'.join('{1:>{0}}: {2}'.format(len(max(keys, key=len)), x, details[x]) for x in keys))
                    if details['JobState'] not in ('PENDING', 'CONFIGURING', 'RUNNING', 'COMPLETING'):
                        break
            except KeyboardInterrupt:
                self._slurm._ssh.exec_command(f'scancel {job}')
                print(f'Canceling job {job}', file=sys.stderr)

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('--quiet', action='store_true', help='Disable progress bar')
    @magic.cell_magic
    def sftp(self, line, cell):
        """File transfer over secure shell.

        Supported commands: cd, chmod, chown, get, lcd, lls, lmkdir, ln, lpwd, ls, mkdir, put, pwd, rename, rm, rmdir, symlink.
        See interactive commands section of http://man.openbsd.org/sftp for details.
        """
        args = magic_arguments.parse_argstring(self.sftp, line)
        lines = [x for x in cell.splitlines() if x.strip() and not x.lstrip().startswith('#')]
        self._slurm.sftp(lines, args.quiet)

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('server', help='Address of server')
    @magic_arguments.argument('--username', help='Username, interactively requested if not provided')
    @magic_arguments.argument('--password', help='Password, interactively requested if not provided')
    @magic.line_magic
    def slogin(self, line):
        """Login to server."""
        args = magic_arguments.parse_argstring(self.slogin, line)
        self._slurm.login(args.server, args.username, args.password)
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
        for _ in self._slurm.script(lines, verbose=True):
            break
