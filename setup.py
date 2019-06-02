import os
import re

import setuptools


def readme():
    filepath = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'README.md')
    with open(filepath) as f:
        return f.read()


def version():
    filepath = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'ipyslurm', '__init__.py')
    with open(filepath) as f:
        version_match = re.search(r"^__version__ = [']([^']*)[']", f.read(), re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Failed to find version string')


setuptools.setup(
    name='ipyslurm',
    version=version(),
    description='IPython extension for interacting with the Slurm Workload Manager from Jupyter notebook',
    long_description=readme(),
    long_description_content_type='text/markdown',
    url='https://auneri.github.io/ipyslurm',
    author='Ali Uneri',
    license='MIT',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3'],
    packages=setuptools.find_packages(),
    install_requires=[
        'ipython>=7',
        'ipywidgets>=7',
        'notebook>=5',
        'paramiko>=2'],
    python_requires='>=3')
