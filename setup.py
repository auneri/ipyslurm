import os

import setuptools


def readme():
    filepath = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'README.md')
    with open(filepath) as f:
        return f.read()


setuptools.setup(
    name='ipyslurm',
    description='IPython extension for interacting with the Slurm Workload Manager from Jupyter notebook',
    long_description=readme(),
    long_description_content_type='text/markdown',
    url='https://auneri.github.io/ipyslurm',
    author='Ali Uneri',
    license='MIT',
    classifiers=[
        'Framework :: IPython',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3'],
    packages=setuptools.find_packages(),
    install_requires=[
        'ipython>=7',
        'ipywidgets>=7',
        'notebook>=5',
        'paramiko>=2.5'],
    python_requires='>=3')
