# ipyslurm

[IPython extension](https://ipython.readthedocs.io/en/stable/config/extensions) for interacting with [Slurm Workload Manager](https://slurm.schedmd.com) from [Jupyter](https://jupyter.readthedocs.io).

[![pypi](https://img.shields.io/pypi/v/ipyslurm.svg)](https://pypi.org/project/ipyslurm)
[![conda-forge](https://img.shields.io/conda/vn/conda-forge/ipyslurm.svg)](https://anaconda.org/conda-forge/ipyslurm)
[![license](https://img.shields.io/github/license/auneri/ipyslurm.svg)](https://github.com/auneri/ipyslurm/blob/main/LICENSE.md)
[![build](https://img.shields.io/github/workflow/status/auneri/ipyslurm/ipyslurm)](https://github.com/auneri/ipyslurm/actions)

## Getting started

Install using `pip install ipyslurm` or `conda install -c conda-forge ipyslurm`.

See [example notebooks](https://github.com/auneri/ipyslurm/tree/main/examples) for different use cases.

## Magic commands

Line magics: `sinteract`, `slogin`, `slogout`, `stail`  
Cell magics: `scommand`, `sbatch`, `sftp`, `swritefile`

Use [?](http://ipython.readthedocs.io/en/stable/interactive/tutorial.html#exploring-your-objects) to get help on individual commands.
