# ipyslurm

[IPython extension](https://ipython.readthedocs.io/en/stable/config/extensions/index.html) for interacting with [Slurm Workload Manager](https://slurm.schedmd.com) from [Jupyter](https://jupyter.readthedocs.io).

[![pypi](https://img.shields.io/pypi/v/ipyslurm.svg)](https://pypi.org/project/ipyslurm)
[![conda-forge](https://img.shields.io/conda/vn/conda-forge/ipyslurm.svg)](https://anaconda.org/conda-forge/ipyslurm)
[![license](https://img.shields.io/github/license/auneri/ipyslurm.svg)](https://github.com/auneri/ipyslurm/blob/master/LICENSE.md)

## Getting started

Install using `pip install ipyslurm` or `conda install -c conda-forge ipyslurm`.

See [tutorial notebook](https://github.com/auneri/ipyslurm/tree/master/examples/tutorial.ipynb) for basic usage.

## Magic commands

Line magics: `slogin`, `slogout`, `sinteract`  
Cell magics: `sbash`, `sbatch`, `sftp`, `swritefile`

Use [?](http://ipython.readthedocs.io/en/stable/interactive/tutorial.html#exploring-your-objects) to get help on individual commands.
