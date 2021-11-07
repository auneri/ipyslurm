import getpass
import time
import timeit

from IPython.core import magic, magic_arguments
from IPython.display import clear_output

from . import slurm


@magic.magics_class
class IPySlurm(magic.Magics):

    def __init__(self, *args, **kwargs):
        super(IPySlurm, self).__init__(*args, **kwargs)
        self._slurm = slurm.Slurm()

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('--tail', type=int, metavar='N', help='Block and print last N lines of the log')
    @magic_arguments.argument('--args', nargs='*', metavar='ARG', help='Additional arguments to sbatch')
    @magic.cell_magic
    def sbatch(self, line, cell=''):
        """Submit a batch script to Slurm."""
        args = magic_arguments.parse_argstring(self.sbatch, line)
        job = self._slurm.sbatch(cell, args.args)
        print(f'Submitted batch job {job}')
        if args.tail is not None:
            try:
                self._slurm.tail(job, lines=args.tail)
            except KeyboardInterrupt:
                self._slurm.scancel(job)
                print(f'Canceling batch job {job}')

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('--period', type=float, metavar='SECONDS', help='Repeat execution with a given periodicity')
    @magic_arguments.argument('--timeout', type=float, metavar='SECONDS', help='Timeout for when used with --period')
    @magic_arguments.argument('--stdout', metavar='VARIABLE', help='Store stdout in variable')
    @magic.cell_magic
    @magic.needs_local_scope
    def scommand(self, line, cell, local_ns):
        """Execute commands on server."""
        args = magic_arguments.parse_argstring(self.scommand, line)
        start = timeit.default_timer()
        try:
            while True:
                stdout = self._slurm.command(cell)
                clear_output(wait=True)
                print(stdout)
                elapsed = timeit.default_timer() - start
                if args.timeout is not None and elapsed > args.timeout:
                    print(f'Timed out after {elapsed:.1f} seconds')
                elif args.period is not None:
                    time.sleep(args.period)
                    continue
                break
        except KeyboardInterrupt:
            pass
        if args.stdout is not None:
            local_ns.update({args.stdout: stdout})

    @magic_arguments.magic_arguments()
    @magic.cell_magic
    def sftp(self, line, cell):
        """File transfer over secure shell.

        Supported commands: cd, chmod, chown, get, lcd, lls, lmkdir, ln, lpwd, lrm, lrmdir, ls, mkdir, put, pwd, rename, rm, rmdir, symlink.
        See http://man.openbsd.org/sftp#INTERACTIVE_COMMANDS for details.
        """
        magic_arguments.parse_argstring(self.sftp, line)
        self._slurm.sftp(cell)

    @magic_arguments.magic_arguments()
    @magic.line_magic
    def sinteract(self, line):
        """Interactive shell."""
        magic_arguments.parse_argstring(self.sinteract, line)
        self._slurm.interact()

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('--server', help='Address of server')
    @magic_arguments.argument('--username', help='Username, interactively requested if not provided')
    @magic_arguments.argument('--password', help='Password, interactively requested if not provided')
    @magic_arguments.argument('--instance', help='An existing slurm instance')
    @magic.line_magic
    @magic.needs_local_scope
    def slogin(self, line, local_ns):
        """Login to server."""
        args = magic_arguments.parse_argstring(self.slogin, line)
        if args.instance is not None:
            self._slurm = local_ns.get(args.instance)
        else:
            username = getpass.getuser() if args.username is None else args.username
            password = getpass.getpass() if args.password is None else args.password
            self._slurm.login(args.server, username, password)

    @magic_arguments.magic_arguments()
    @magic.line_magic
    def slogout(self, line):
        """Logout of server."""
        magic_arguments.parse_argstring(self.slogout, line)
        self._slurm.logout()

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('filepath', help='Path of file')
    @magic_arguments.argument('--append', action='store_true', help='Append contents of the cell to an existing file')
    @magic.cell_magic
    def swritefile(self, line, cell):
        args = magic_arguments.parse_argstring(self.swritefile, line)
        self._slurm.writefile(args.filepath, cell, append=args.append)
