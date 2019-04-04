# Release Instructions

1. Create a new tag
    * update `__version__` and `CHANGELOG` with commit with message "Release vX.X.X"
    * tag with message "Release vX.X.X"
    * push changes to https://github.com/auneri/ipyslurm

2. Upload new package to PyPI

    ```bash
    pushd $IPYSLURM_PATH
    conda activate $CONDA_ENVIRONMENT
    python setup.py sdist bdist_wheel
    conda activate base
    twine upload dist/*
    conda deactivate
    popd
    ```

3. Upload new package to conda-forge
    * update `version` (should match `__version__`) and `hash` (should match PyPI) in `recipe/meta.yaml`
    * make a pull request to https://github.com/conda-forge/ipyslurm-feedstock
