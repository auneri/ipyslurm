# Tips for using ipyslurm on MARCC

([Maryland Advanced Research Computing Center](https://www.marcc.jhu.edu))

Perform `ftp` operations over a dedicated data server:

```shell
%slogin gateway2.marcc.jhu.edu --username my_username --data-server dtn2.marcc.jhu.edu
```

Modify `.bashrc` for faster cell execution:

```shell
%%swritefile ~/.bashrc
# skip sourcing z01_sbalance.sh
for script in /etc/profile.d/*[^z01_status]*.sh; do . $script; done
# load modules in a single statement
module load cuda/9.2 python/3.6-anaconda
```

Display balance and disk usage:

```shell
%%sbash
sbalance
du --human-readable --max-depth 2 --separate-dirs my_folder | sort --human-numeric-sort --reverse
```

Reuse `sbatch` arguments:

```python
gpuk80 = ' '.join((
    '--cpus-per-task 6',
    '--gres gpu:1',
    '--nodes 1',
    '--ntasks-per-node 1',
    '--partition gpuk80'))
```

```shell
%%sbatch --args "{gpuk80}"
#SBATCH --job-name my_script
#SBATCH --time 01:00:00
python my_script.py
```
