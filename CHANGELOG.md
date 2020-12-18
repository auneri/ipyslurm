# ipyslurm Changelog

This project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html)
and the format of this document is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/).

## Unreleased
See [individual commits](https://github.com/auneri/ipyslurm/compare/v1.6.0...master) for detailed changes.

## 1.6.0 -- 2020-12-18
See [individual commits](https://github.com/auneri/ipyslurm/compare/v1.5.0...v1.6.0) for detailed changes.
* Support `ls`, `mkdir`, and `rmdir` in `sftp` cell magic ([5896e26](https://github.com/auneri/ipyslurm/commit/5896e2620fb6c818a5aec880063cb054a3da0560))
* Various fixed, including escaping paths with spaces ([cea8407](https://github.com/auneri/ipyslurm/commit/cea84070b4fff91ff89df4469f3fdf1a2e17c128))
* Continuous integration using GitHub Actions ([08ec92a](https://github.com/auneri/ipyslurm/commit/08ec92aa802ac547b00e4f13ebc6a58fa00c7add))

## 1.5.0 -- 2019-12-10
See [individual commits](https://github.com/auneri/ipyslurm/compare/v1.4.0...v1.5.0) for detailed changes.
* New `sshell` line magic, supersedes `sinteract` ([c5fa56f](https://github.com/auneri/ipyslurm/commit/c5fa56fd6e01c24f9ebff78030a9162c1429572c))
* Block bash commands to avoid flooding server on period calls ([cd5034e](https://github.com/auneri/ipyslurm/commit/cd5034efa4e0eb44de80029ca73bc9b31ec9d314))
* Project is properly marked as an IPython extension ([f42c812](https://github.com/auneri/ipyslurm/commit/f42c8124a8b7360f9f3f0b7bbc08883a32a9ef08))

## 1.4.0 -- 2019-10-21
See [individual commits](https://github.com/auneri/ipyslurm/compare/v1.3.0...v1.4.0) for detailed changes.
* New `sftp` remote commands `rm` and `rmdir` ([73f680d](https://github.com/auneri/ipyslurm/commit/73f680d05b16279b11b05be5dcc6693ba49530c9))
* New `sftp` local commands `lrm` and `lrmdir` ([8e4256a](https://github.com/auneri/ipyslurm/commit/8e4256abd687c45ba98a9afccbe0920c09f6a14c))
* New `sbatch` line magic ([cac3fed](https://github.com/auneri/ipyslurm/commit/cac3fed2f23da34bff10d10aa883b00d34fc7f67))
* Minimum required `paramiko` is v2.5 ([f26612e](https://github.com/auneri/ipyslurm/commit/f26612e11371a73fe4dda1022b6d4f946da00797))

## 1.3.0 -- 2019-06-03
See [individual commits](https://github.com/auneri/ipyslurm/compare/v1.2.0...v1.3.0) for detailed changes.
* Dropped support for Python v2 ([c9fadd1](https://github.com/auneri/ipyslurm/commit/c9fadd18857f699cb78ede22b40175528926210e))
* Respect local/remote working directory in sftp ([64dec86](https://github.com/auneri/ipyslurm/commit/64dec864ed45da964b7573b51897f992b106992b))
* Custom sftp progress using ipywidgets ([009736a](https://github.com/auneri/ipyslurm/commit/009736a72aa57261028fd2f678bfa39290719752))
* Improved error handling and reporting

## 1.2.0 -- 2019-04-03
See [individual commits](https://github.com/auneri/ipyslurm/compare/v1.1.0...v1.2.0) for detailed changes.
* Support for IPython v7.4 ([f50df94](https://github.com/auneri/ipyslurm/commit/f50df941d808147f3b6ac313f287d060bfa49984))

## 1.1.0 -- 2018-10-05
See [individual commits](https://github.com/auneri/ipyslurm/compare/v1.0.0...v1.1.0) for detailed changes.
* New `swritefile` magic ([4206b5a](https://github.com/auneri/ipyslurm/commit/4206b5a4abf85c645d10a717288a982d56e3724e))
* Usage tips on MARCC ([09edb73](https://github.com/auneri/ipyslurm/commit/09edb731ee167b7abca96441afcca1d27d5956dd))
* Hosting on conda-forge ([#2](https://github.com/auneri/ipyslurm/issues/2))
* This very changelog!

## 1.0.0 -- 2018-07-09
Initial release!
