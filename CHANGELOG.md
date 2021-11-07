# ipyslurm Changelog

This project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html)
and the format of this document is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/).

## Unreleased

See [individual commits](https://github.com/auneri/ipyslurm/compare/v2.0.0...main) for detailed changes.

## 2.0.0 -- 2021-11-07

See [individual commits](https://github.com/auneri/ipyslurm/compare/v1.6.0...v2.0.0) for detailed changes.

* Backwards incompatible changes, e.g., renamed magics ([link](https://github.com/auneri/ipyslurm/commit/9261914b))
* Refactor slurm module for standalone use ([link](https://github.com/auneri/ipyslurm/commit/c2401c86))
* Dropped custom logic to support MARCC ([link](https://github.com/auneri/ipyslurm/commit/a6c373ea))

## 1.6.0 -- 2020-12-18

See [individual commits](https://github.com/auneri/ipyslurm/compare/v1.5.0...v1.6.0) for detailed changes.

* Support `ls`, `mkdir`, and `rmdir` in `sftp` cell magic ([link](https://github.com/auneri/ipyslurm/commit/5896e26))
* Various fixes, including escaping paths with spaces ([link](https://github.com/auneri/ipyslurm/commit/cea8407))
* Continuous integration using GitHub Actions ([link](https://github.com/auneri/ipyslurm/commit/08ec92a))

## 1.5.0 -- 2019-12-10

See [individual commits](https://github.com/auneri/ipyslurm/compare/v1.4.0...v1.5.0) for detailed changes.

* New `sshell` line magic, supersedes `sinteract` ([link](https://github.com/auneri/ipyslurm/commit/c5fa56f))
* Block bash commands to avoid flooding server on period calls ([link](https://github.com/auneri/ipyslurm/commit/cd5034e))
* Project is properly marked as an IPython extension ([link](https://github.com/auneri/ipyslurm/commit/f42c812))

## 1.4.0 -- 2019-10-21

See [individual commits](https://github.com/auneri/ipyslurm/compare/v1.3.0...v1.4.0) for detailed changes.

* New `sftp` remote commands `rm` and `rmdir` ([link](https://github.com/auneri/ipyslurm/commit/73f680d))
* New `sftp` local commands `lrm` and `lrmdir` ([link](https://github.com/auneri/ipyslurm/commit/8e4256a))
* New `sbatch` line magic ([link](https://github.com/auneri/ipyslurm/commit/cac3fed))
* Minimum required `paramiko` is v2.5 ([link](https://github.com/auneri/ipyslurm/commit/f26612e))

## 1.3.0 -- 2019-06-03

See [individual commits](https://github.com/auneri/ipyslurm/compare/v1.2.0...v1.3.0) for detailed changes.

* Dropped support for Python v2 ([link](https://github.com/auneri/ipyslurm/commit/c9fadd1))
* Respect local/remote working directory in sftp ([link](https://github.com/auneri/ipyslurm/commit/64dec86))
* Custom sftp progress using ipywidgets ([link](https://github.com/auneri/ipyslurm/commit/009736a))
* Improved error handling and reporting

## 1.2.0 -- 2019-04-03

See [individual commits](https://github.com/auneri/ipyslurm/compare/v1.1.0...v1.2.0) for detailed changes.

* Support for IPython v7.4 ([link](https://github.com/auneri/ipyslurm/commit/f50df94))

## 1.1.0 -- 2018-10-05

See [individual commits](https://github.com/auneri/ipyslurm/compare/v1.0.0...v1.1.0) for detailed changes.

* New `swritefile` magic ([link](https://github.com/auneri/ipyslurm/commit/4206b5a))
* Usage tips on MARCC ([link](https://github.com/auneri/ipyslurm/commit/09edb73))
* Hosting on conda-forge ([link](https://github.com/auneri/ipyslurm/issues/2))
* This very changelog!

## 1.0.0 -- 2018-07-09

Initial release!
