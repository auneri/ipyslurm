# ipyslurm Release Instructions

1. Create a new tag

    * Update `version` and `CHANGELOG` with commit message "Release vX.X.X"
    * Add tag with message "Release vX.X.X"
    * Push changes to [ipyslurm](https://github.com/auneri/ipyslurm)

2. Upload new package to PyPI

    ```shell
    git clone --depth 1 --branch vX.X.X https://github.com/auneri/ipyslurm src
    conda create --yes --prefix ./env --channel conda-forge python=3.10 build twine
    conda activate ./env
    cd src
    python -m build
    python -m twine upload dist/*
    ```

3. Upload new package to conda-forge

    * If a pull request is not automatically triggered within 24 hr of the PyPI release:
    * Make a pull request to [ipyslurm-feedstock](https://github.com/conda-forge/ipyslurm-feedstock)
    * Update `version` and `hash` (should match PyPI) in `recipe/meta.yaml`
