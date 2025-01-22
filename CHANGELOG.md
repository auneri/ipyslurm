# ipyslurm Changelog

This project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html)
and the format of this document is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/).

## Unreleased

See [individual commits](https://github.com/auneri/ipyslurm/compare/v2.3.0...main) for detailed changes.

## 2.3.0 -- 2025-01-22

* Update packaging to use pyproject.toml.
* Deploy project using GitHub actions.
* Make ipywidgets a soft dependency.
* Explicitly use text progress bars.
* Show output only for pending or running jobs.
* Speedup tail to support large job arrays.
* Create directory structures as needed.
* Use temporary files instead of ~/.ipylurm.
* Prevent rm/lrm errors if path does not exist.

## 2.2.0 -- 2023-11-21

* Option to repeat tail output, true by default.
* Replace carriage return with newline in tail.
* Make ipywidgets a a soft dependency.
* Various improvements to the CI configuration.
* Specify minimum dependency versions, use conda-forge.
* Do not overload repr, provide slurm.server as a property.
* Handle paramiko SSH exceptions, do not load system SSH keys.

## 2.1.0 -- 2021-11-10

* New example notebooks demonstrating basic and advanced use from Python.
* Separate stail from sbatch to match the Python interface.
* Allow passing slurm instance to magics.
* Prevent output flicker.
* Reintroduce login support for MARCC and potentially other clusters.
* Various fixes for errors introduced in previous release.

## 2.0.0 -- 2021-11-07

* Backwards incompatible changes, e.g., renamed magics.
* Refactor slurm module for standalone use.
* Dropped custom logic to support MARCC.

## 1.6.0 -- 2020-12-18

* Support `ls`, `mkdir`, and `rmdir` in `sftp` cell magic.
* Various fixes, including escaping paths with spaces.
* Continuous integration using GitHub Actions.

## 1.5.0 -- 2019-12-10

* New `sshell` line magic, supersedes `sinteract`.
* Block bash commands to avoid flooding server on period calls.
* Project is properly marked as an IPython extension.

## 1.4.0 -- 2019-10-21

* New `sftp` remote commands `rm` and `rmdir`.
* New `sftp` local commands `lrm` and `lrmdir`.
* New `sbatch` line magic.
* Minimum required `paramiko` is v2.5.

## 1.3.0 -- 2019-06-03

* Dropped support for Python v2.
* Respect local/remote working directory in sftp.
* Custom sftp progress using ipywidgets.
* Improved error handling and reporting.

## 1.2.0 -- 2019-04-03

* Support for IPython v7.4.

## 1.1.0 -- 2018-10-05

* New `swritefile` magic.
* Usage tips on MARCC.
* Hosting on conda-forge.
* This very changelog!

## 1.0.0 -- 2018-07-09

Initial release!
