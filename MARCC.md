# Tips for using ipyslurm on MARCC

([Maryland Advanced Research Computing Center](https://www.marcc.jhu.edu))

Perform `ftp` operations over a dedicated server:

```sh
%slogin gateway2.marcc.jhu.edu --username my_username --data-server dtn2.marcc.jhu.edu
```

Modify `.bashrc` for faster cell execution:

```sh
%%swritefile ~/.bashrc
for script in /etc/profile.d/*.sh; do
    # skip z01_mybalance and z02_homeQuota
    if [[ $script != /etc/profile.d/z0[^0]*.sh ]]; then
        source $script
    fi
done
unset script
# module loads in a single statement
module load cuda/9.2 python/3.6-anaconda
# activate your conda environment
source activate my_environment
```

Display balance and disk usage:

```sh
%%sbash
sbalance
du --human-readable --max-depth 2 --separate-dirs ~/my_folder | sort --human-numeric-sort --reverse
```

Reuse `sbatch` arguments:

```python
sbatch_args = ' '.join([
    '--partition', 'gpuk80',
    '--gres', 'gpu:1',
    '--ntasks-per-node', '1',
    '--cpus-per-task', '6'])
```

```sh
%%sbatch --args "{sbatch_args}"
#SBATCH --job-name my_script
#SBATCH --time 01:00:00
python my_script.py
```
