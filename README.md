# ipyslurm

[IPython extension](https://ipython.readthedocs.io/en/stable/config/extensions/index.html) for interacting with [Slurm Workload Manager](https://slurm.schedmd.com) from [Jupyter](https://jupyter.readthedocs.io).

[![license](https://img.shields.io/github/license/auneri/ipyslurm.svg)](https://github.com/auneri/ipyslurm/blob/master/LICENSE.md)

## Getting Started

Install using `pip install git+https://github.com/auneri/ipyslurm.git`.

See [tutorial notebook](https://github.com/auneri/ipyslurm/tree/master/examples/tutorial.ipynb) for basic usage.

## Magic Commands

```
%slogin [-s | --server <arg>]
        [-u | --username <arg>]
        [-p | --password <arg>]
        [-d | --data-server <arg>]
```

```
%slogout
```

```
%sinteract
```

```
%%sbash [-p | --period <arg>]
        [-t | --timeout <arg>]
        [-so | --stdout <arg>]
        [-se | --stderr <arg>]
```

```
%%sbatch [-w | --wait]
         [-t | --tail <arg>]
         [-a | --args <arg>]
```

```
%%sftp [-v | --verbose]
       [-d | --dryrun]
       [-i | --instructions <arg>]
```
