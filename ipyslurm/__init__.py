from .version import __version__  # noqa: F401
from .slurm import Slurm  # noqa: F401, I100

try:
    from .magic import SlurmMagics

    def load_ipython_extension(ipython):
        ipython.register_magics(SlurmMagics)
except ModuleNotFoundError:
    pass
