# ipyslurm Release Instructions

1. Create a new tag
    * update `__version__` and `CHANGELOG` with commit message "Release vX.X.X"
    * add tag with message "Release vX.X.X"
    * push changes to [ipyslurm](https://github.com/auneri/ipyslurm)

2. Upload new package to PyPI

    ```bash
    git clone --depth 1 --branch vX.X.X https://github.com/auneri/ipyslurm src
    conda create --yes --prefix env python=3.10 setuptools
    conda activate ./env
    cd src
    python setup.py sdist bdist_wheel
    conda activate base
    twine upload dist/*
    ```

3. Upload new package to conda-forge
    * make a pull request to [ipyslurm-feedstock](https://github.com/conda-forge/ipyslurm-feedstock)
    * update `version` (should match `__version__`) and `hash` (should match PyPI) in `recipe/meta.yaml`
