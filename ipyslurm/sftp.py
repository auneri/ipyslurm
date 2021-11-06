import datetime
import importlib
import os
import re
import shlex
import stat

from tqdm.auto import tqdm


class SFTP:

    def __init__(self, ssh):
        self.ssh = ssh
        self.ftp = self.ssh.open_sftp()

    def __del__(self):
        self.ftp.close()

    def exec_commands(self, cell, quiet=False):
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
        lines = [x for x in cell.splitlines() if x.strip() and not x.lstrip().startswith('#')]
        ssh, ftp = self.ssh, self.ftp
        pbars = [tqdm(desc=x.split()[0], position=0) if any(x.split()[0] == y for y in ('get', 'put', 'rm')) else None for x in lines]
        for line, pbar in zip(lines, pbars):
            argv = shlex.split(line, posix=False)
            command = commands.get(argv[0])
            if command is None:
                raise SyntaxError(f'"{argv[0]}" is not supported')
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
                            get(ftp, f'{dirpath}/{filename}', os.path.join(root, filename), resume)
                            pbar.update()
                        if not recurse:
                            break
                else:
                    pbar.reset(1)
                    get(ftp, remote, local, resume)
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
                            put(ftp, os.path.join(dirpath, filename), f'{root}/{filename}', resume)
                            pbar.update()
                        if not recurse:
                            break
                else:
                    pbar.reset(1)
                    put(ftp, local, remote, resume)
                    pbar.update()
                pbar.close()
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
                else:
                    pbar.reset(1)
                    os.remove(local)
                    pbar.update()
                pbar.close()
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
                            ftp.remove(f'{dirpath}/{filename}')
                            pbar.update()
                        for dirname in dirnames:
                            ftp.rmdir(f'{dirpath}/{dirname}')
                    ftp.rmdir(remote)
                else:
                    pbar.reset(1)
                    ftp.remove(remote)
                    pbar.update()
                pbar.close()
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
            path = f'{cwd}/{path}'
        stdouts, _ = ssh.exec_command(f'readlink -f "{path}"', verbose=False)
        if len(stdouts) != 1:
            raise OSError(f'Failed to find {path}')
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
            for x in walk(ftp, dirpath, topdown, followlinks):
                yield x
    if not topdown:
        yield top, [x.filename for x in dirnames], [x.filename for x in filenames]
