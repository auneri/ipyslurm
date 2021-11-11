import time
import timeit

from IPython.core import magic, magic_arguments
from IPython.display import clear_output

from . import slurm


@magic.magics_class
class SlurmMagics(magic.Magics):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._slurm = slurm.Slurm()

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('--args', nargs='*', help='Additional arguments to sbatch')
    @magic_arguments.argument('--job', help='Store job ID in variable', metavar='VARIABLE')
    @magic_arguments.argument('--instance', help='Existing slurm instance', metavar='VARIABLE')
    @magic.needs_local_scope
    @magic.cell_magic
    def sbatch(self, line, cell, local_ns):
        """Submit a batch script to Slurm."""
        args = magic_arguments.parse_argstring(self.sbatch, line)
        slurm = local_ns.get(args.instance, self._slurm)
        job = slurm.sbatch(cell, args.args)
        print(f'Submitted batch job {job}')
        if args.job is not None:
            local_ns.update({args.job: job})

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('--period', type=float, help='Repeat execution with a given periodicity', metavar='SECONDS')
    @magic_arguments.argument('--timeout', type=float, help='Timeout for when used with --period', metavar='SECONDS')
    @magic_arguments.argument('--stdout', help='Store stdout in variable', metavar='VARIABLE')
    @magic_arguments.argument('--instance', help='Existing slurm instance', metavar='VARIABLE')
    @magic.needs_local_scope
    @magic.cell_magic
    def scommand(self, line, cell, local_ns):
        """Execute commands on server."""
        args = magic_arguments.parse_argstring(self.scommand, line)
        slurm = local_ns.get(args.instance, self._slurm)
        start = timeit.default_timer()
        try:
            while True:
                stdout = slurm.command(cell)
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
    @magic_arguments.argument('--instance', help='Existing slurm instance', metavar='VARIABLE')
    @magic.needs_local_scope
    @magic.cell_magic
    def sftp(self, line, cell, local_ns):
        """File transfer over secure shell.

        Supported commands: cd, chmod, chown, get, lcd, lls, lmkdir, ln, lpwd, lrm, lrmdir, ls, mkdir, put, pwd, rename, rm, rmdir, symlink.
        See https://man.openbsd.org/sftp#INTERACTIVE_COMMANDS for details.
        """
        args = magic_arguments.parse_argstring(self.sftp, line)
        slurm = local_ns.get(args.instance, self._slurm)
        slurm.sftp(cell)

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('--instance', help='Existing slurm instance', metavar='VARIABLE')
    @magic.needs_local_scope
    @magic.line_magic
    def sinteract(self, line, local_ns):
        """Interactive shell."""
        args = magic_arguments.parse_argstring(self.sinteract, line)
        slurm = local_ns.get(args.instance, self._slurm)
        slurm.interact()

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('--server', help='Address of server', metavar='ADDRESS')
    @magic_arguments.argument('--username', help='Username, interactively requested if not provided')
    @magic_arguments.argument('--password', help='Password, interactively requested if not provided')
    @magic.line_magic
    def slogin(self, line):
        """Login to server."""
        args = magic_arguments.parse_argstring(self.slogin, line)
        self._slurm.login(args.server, args.username, args.password)

    @magic_arguments.magic_arguments()
    @magic.line_magic
    def slogout(self, line):
        """Logout of server."""
        magic_arguments.parse_argstring(self.slogout, line)
        self._slurm.logout()

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('job', help='Job ID')
    @magic_arguments.argument('--lines', default=1, type=int, help='Print last N lines of the log', metavar='N')
    @magic_arguments.argument('--instance', help='Existing slurm instance', metavar='VARIABLE')
    @magic.needs_local_scope
    @magic.line_magic
    def stail(self, line, local_ns):
        """Logout of server."""
        args = magic_arguments.parse_argstring(self.stail, line)
        slurm = local_ns.get(args.instance, self._slurm)
        slurm.tail(args.job, lines=args.lines)

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('filepath', help='Path of file')
    @magic_arguments.argument('--append', action='store_true', help='Append contents of the cell to an existing file')
    @magic_arguments.argument('--instance', help='Existing slurm instance', metavar='VARIABLE')
    @magic.needs_local_scope
    @magic.cell_magic
    def swritefile(self, line, cell, local_ns):
        args = magic_arguments.parse_argstring(self.swritefile, line)
        slurm = local_ns.get(args.instance, self._slurm)
        slurm.writefile(args.filepath, cell, append=args.append)
