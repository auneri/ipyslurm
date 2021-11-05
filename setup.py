import inspect
import pathlib

import setuptools


def read(filename):
    filepath = pathlib.Path(inspect.getfile(inspect.currentframe())).resolve().parent / filename
    with filepath.open() as f:
        return f.read()


setuptools.setup(
    name='ipyslurm',
    description='IPython extension for interacting with the Slurm Workload Manager from Jupyter notebook',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    url='https://auneri.github.io/ipyslurm',
    author='Ali Uneri',
    license='MIT',
    license_files=('LICENSE.md',),
    classifiers=[
        'Framework :: IPython',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3'],
    packages=setuptools.find_packages(),
    install_requires=[
        'ipython',
        'ipywidgets',
        'paramiko'],
    python_requires='>=3.7')
