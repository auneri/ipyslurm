# ipyslurm

Python interface to [Slurm Workload Manager](https://slurm.schedmd.com).

[![license](https://img.shields.io/github/license/auneri/ipyslurm)](https://github.com/auneri/ipyslurm/blob/main/LICENSE.md)
[![build](https://img.shields.io/github/actions/workflow/status/auneri/ipyslurm/main.yml)](https://github.com/auneri/ipyslurm/actions)
[![pypi](https://img.shields.io/pypi/v/ipyslurm)](https://pypi.org/project/ipyslurm)
[![conda-forge](https://img.shields.io/conda/vn/conda-forge/ipyslurm)](https://anaconda.org/conda-forge/ipyslurm)

## Getting started

Install using `pip install ipyslurm` or `conda install -c conda-forge ipyslurm`.

See [example notebooks](https://github.com/auneri/ipyslurm/tree/main/examples) for different use cases.

## Magic commands

Line magics: `sinteract`, `slogin`, `slogout`, `stail`  
Cell magics: `scommand`, `sbatch`, `sftp`, `swritefile`

Use [?](http://ipython.readthedocs.io/en/stable/interactive/tutorial.html#exploring-your-objects) to get help on individual commands.

## Releasing a new version

1. Update `project.version` in `pyproject.toml` and `CHANGELOG` with commit message "Release vX.X.X".
2. Add tag vX.X.X with message "Release vX.X.X".
3. Push the tag and create a new release on [ipyslurm](https://github.com/auneri/ipyslurm).
4. Merge the auto-generated pull request on [ipyslurm-feedstock](https://github.com/conda-forge/ipyslurm-feedstock).
