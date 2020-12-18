# Tips for using ipyslurm on MARCC

([Maryland Advanced Research Computing Center](https://www.marcc.jhu.edu))

Perform `ftp` operations over a dedicated data server:

```shell
%slogin login.marcc.jhu.edu --username my_username
```

Customize default modules:

```shell
%%sbash
rm -f ~/.lmod.d/default
module reset
module unload MARCC
module load centos7/current cuda/10.1
module save
```

Display balance and disk usage:

```shell
%%sbash
sbalance
scratchquota
du --human-readable --max-depth 1 $HOME | sort --human-numeric-sort --reverse
```

Reuse `sbatch` arguments:

```python
def gpuk80(ngpu=1, **kwargs):
    kwargs.setdefault('cpus-per-task', 6)
    kwargs.setdefault('gres', f'gpu:{ngpu}')
    kwargs.setdefault('nodes', 1)
    kwargs.setdefault('ntasks-per-node', ngpu)
    kwargs.setdefault('partition', 'gpuk80')
    return ' '.join(f'--{key} {value}' for key, value in kwargs.items())
```

```shell
%%sbatch --args "{gpuk80()}"
#SBATCH --job-name my_script
#SBATCH --time 01:00:00
python my_script.py
```
