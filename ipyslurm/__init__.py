from .version import __version__  # noqa: F401
from .magic import SlurmMagics  # noqa: I100
from .slurm import Slurm  # noqa: F401


def load_ipython_extension(ipython):
    ipython.register_magics(SlurmMagics)
