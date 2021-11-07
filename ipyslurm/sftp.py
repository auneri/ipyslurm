import datetime
import importlib
import logging
import os
import shlex
import stat

from tqdm.auto import tqdm

from .util import sort_key_natural

PBAR_FUNCTIONS = 'get', 'lrm', 'put', 'rm'
SFTP_FUNCTIONS = {
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


class SFTP:

    def __init__(self, ssh):
        self.ssh = ssh
        self.ftp = self.ssh.open_sftp()

    def __del__(self):
        self.ftp.close()

    def exec_commands(self, commands):
        pbars = [tqdm(desc=x.split()[0], position=0) if any(x.split()[0] == y for y in PBAR_FUNCTIONS) else None for x in commands]
        for command, pbar in zip(commands, pbars):
            argv = shlex.split(command, posix=False)
            function = SFTP_FUNCTIONS.get(argv[0])
            if function is None:
                raise NotImplementedError(f'"{argv[0]}" is not supported')
            else:
                logging.getLogger('ipyslurm.sftp').debug('Executing SFTP command "{argv[0]}"')
            if argv[0] == 'cd':
                if len(argv) != 2:
                    raise ValueError('cd remote_directory')
                output = getattr(self.ftp, function)(self.normalize(argv[1]))
            elif argv[0] == 'get':
                recurse = bool([x for x in argv if x.startswith('-') and 'r' in x])
                resume = bool([x for x in argv if x.startswith('-') and 'a' in x])
                argv = [x for x in argv if not x.startswith('-')]
                if len(argv) == 2:
                    argv.append(argv[-1])
                elif len(argv) != 3:
                    raise ValueError('get [-ra] remote_file [local_file]')
                local, remote = self.lnormalize(argv[2]), self.normalize(argv[1])
                if stat.S_ISDIR(self.ftp.stat(remote).st_mode):
                    pbar.reset(sum(len(filenames) for i, (_, _, filenames) in enumerate(self.walk(remote)) if recurse or i == 0))
                    for dirpath, _, filenames in self.walk(remote):
                        root = local + os.path.sep.join(dirpath.replace(remote, '').split('/'))
                        try:
                            os.mkdir(root)
                        except OSError:
                            pass
                        for filename in filenames:
                            self.get(f'{dirpath}/{filename}', os.path.join(root, filename), resume)
                            pbar.update()
                        if not recurse:
                            break
                else:
                    pbar.reset(1)
                    self.get(remote, local, resume)
                    pbar.update()
                pbar.close()
            elif argv[0] == 'put':
                recurse = bool([x for x in argv if x.startswith('-') and 'r' in x])
                resume = bool([x for x in argv if x.startswith('-') and 'a' in x])
                argv = [x for x in argv if not x.startswith('-')]
                if len(argv) == 2:
                    argv.append(argv[-1])
                elif len(argv) != 3:
                    raise ValueError('put [-ra] local_file [remote_file]')
                local, remote = self.lnormalize(argv[1]), self.normalize(argv[2])
                if os.path.isdir(local):
                    pbar.reset(sum(len(filenames) for i, (_, _, filenames) in enumerate(os.walk(local)) if recurse or i == 0))
                    for dirpath, _, filenames in os.walk(local):
                        root = remote + '/'.join(dirpath.replace(local, '').split(os.path.sep))
                        try:
                            self.ftp.mkdir(root)
                        except OSError:
                            pass
                        for filename in filenames:
                            self.put(os.path.join(dirpath, filename), f'{root}/{filename}', resume)
                            pbar.update()
                        if not recurse:
                            break
                else:
                    pbar.reset(1)
                    self.put(local, remote, resume)
                    pbar.update()
                pbar.close()
            elif argv[0] == 'lcd':
                if len(argv) != 2:
                    raise ValueError('lcd local_directory')
                output = getattr(importlib.import_module(function.rsplit('.', 1)[0]), function.rsplit('.', 1)[1])(self.lnormalize(argv[1]))
            elif argv[0] in ('lls', 'lmkdir', 'lpwd', 'lrmdir'):
                output = getattr(importlib.import_module(function.rsplit('.', 1)[0]), function.rsplit('.', 1)[1])(*argv[1:])
            elif argv[0] == 'lrm':
                recurse = bool([x for x in argv if x.startswith('-') and 'r' in x])
                argv = [x for x in argv if not x.startswith('-')]
                if len(argv) != 2:
                    raise ValueError('lrm [-r] local_file')
                local = self.lnormalize(argv[1])
                if recurse and os.path.isdir(local):
                    pbar.reset(sum(len(filenames) for i, (_, _, filenames) in enumerate(os.walk(local, topdown=False))), style='danger')
                    for dirpath, dirnames, filenames in os.walk(local, topdown=False):
                        for filename in filenames:
                            os.remove(os.path.join(dirpath, filename))
                            pbar.update()
                        for dirname in dirnames:
                            os.rmdir(os.path.join(dirpath, dirname))
                    os.rmdir(local)
                else:
                    pbar.reset(1)
                    os.remove(local)
                    pbar.update()
                pbar.close()
            elif argv[0] == 'ls':
                if len(argv) != 2:
                    raise ValueError('ls remote_directory')
                output = getattr(self.ftp, function)(self.normalize(argv[1]))
            elif argv[0] == 'mkdir':
                if len(argv) != 2:
                    raise ValueError('mkdir remote_directory')
                output = getattr(self.ftp, function)(self.normalize(argv[1]))
            elif argv[0] == 'rm':
                recurse = bool([x for x in argv if x.startswith('-') and 'r' in x])
                argv = [x for x in argv if not x.startswith('-')]
                if len(argv) != 2:
                    raise ValueError('rm [-r] remote_file')
                remote = self.normalize(argv[1])
                if recurse and stat.S_ISDIR(self.ftp.stat(remote).st_mode):
                    pbar.reset(sum(len(filenames) for i, (_, _, filenames) in enumerate(self.walk(remote, topdown=False))), style='danger')
                    for dirpath, dirnames, filenames in self.walk(remote, topdown=False):
                        for filename in filenames:
                            self.ftp.remove(f'{dirpath}/{filename}')
                            pbar.update()
                        for dirname in dirnames:
                            self.ftp.rmdir(f'{dirpath}/{dirname}')
                    self.ftp.rmdir(remote)
                else:
                    pbar.reset(1)
                    self.ftp.remove(remote)
                    pbar.update()
                pbar.close()
            elif argv[0] == 'rmdir':
                if len(argv) != 2:
                    raise ValueError('rmdir remote_directory')
                output = getattr(self.ftp, function)(self.normalize(argv[1]))
            else:  # 'chmod', 'chown', 'ln', 'pwd', 'rename', 'symlink'
                output = getattr(self.ftp, function)(*argv[1:])
            if argv[0] in ('pwd', 'lpwd'):
                print(output)
            elif argv[0] in ('ls', 'lls'):
                print('\n'.join(sorted(output, key=sort_key_natural)))

    def get(self, remote, local, resume=False):
        try:
            if not resume:
                raise OSError
            remote_timestamp = datetime.datetime.fromtimestamp(self.ftp.stat(remote).st_mtime)
            local_timestamp = datetime.datetime.fromtimestamp(os.stat(local)[stat.ST_MTIME])
            if remote_timestamp > local_timestamp:
                raise OSError
        except OSError:
            self.ftp.get(remote, local)
            stats = self.ftp.stat(remote)
            os.utime(local, (stats.st_atime, stats.st_mtime))

    def lnormalize(self, path):
        if path.startswith('"'):
            path = path.replace('"', '')
        elif path.startswith("'"):
            path = path.replace("'", '')
        return os.path.abspath(os.path.expanduser(path))

    def normalize(self, path):
        if path.startswith('"'):
            path = path.replace('"', '')
        elif path.startswith("'"):
            path = path.replace("'", '')
        cwd = self.ftp.getcwd()
        if cwd is not None:
            path = f'{cwd}/{path}'
        stdouts = self.ssh.exec_command(f'readlink -f "{path}"')
        if len(stdouts) != 1:
            raise FileNotFoundError(f'Failed to find {path}')
        return stdouts[0]

    def put(self, local, remote, resume=False):
        try:
            if not resume:
                raise OSError
            local_timestamp = datetime.datetime.fromtimestamp(os.stat(local)[stat.ST_MTIME])
            remote_timestamp = datetime.datetime.fromtimestamp(self.ftp.stat(remote).st_mtime)
            if local_timestamp > remote_timestamp:
                raise OSError
        except OSError:
            self.ftp.put(local, remote)
            stats = os.stat(local)
            self.ftp.utime(remote, (stats.st_atime, stats.st_mtime))

    def walk(self, top, topdown=True, followlinks=False):
        dirnames, filenames = [], []
        try:
            attrs = self.ftp.listdir_attr(top)
        except FileNotFoundError:
            raise FileNotFoundError(f'Failed to list contents of "{top}"')
        for attr in attrs:
            if stat.S_ISDIR(attr.st_mode):
                dirnames.append(attr)
            else:
                filenames.append(attr)
        if topdown:
            yield top, [x.filename for x in dirnames], [x.filename for x in filenames]
        for attr in dirnames:
            dirpath = f'{top}/{attr.filename}'
            if followlinks or not stat.S_ISLNK(attr.st_mode):
                for x in self.walk(dirpath, topdown, followlinks):
                    yield x
        if not topdown:
            yield top, [x.filename for x in dirnames], [x.filename for x in filenames]
