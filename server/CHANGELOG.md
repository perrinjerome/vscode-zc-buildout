# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog][keepachangelog],
and this project adheres to [Semantic Versioning][semver].

## Unreleased

## [0.9.3] - 2023-09-19

### Fixed

- server: Fix crash when hover .cfg.in in gitlens views
- client,server: update dependencies

## [0.9.2] - 2023-02-24

### Fixed

- server: fixed definition of `python_requires`

## [0.9.1] - 2023-02-24

### Added

- client: version up dependencies

## [0.9.0] - 2023-01-01

### Added

- update to pygls 1.0

## [0.8.3] - 2022-11-06

### Fixed

- client: revert to older vscode and vscode-languageclient dependencies

### Added

- server: support more slapos recipes

## [0.8.2] - 2022-10-29

### Fixed:

- client: install with requirements.txt to install a fixed version

### Added:

- client: version up dependencies
- server: support python 3.11

## [0.8.1] - 2022-07-03

### Fixed:

- code_actions: fix visit project on pypi when invoked from option key
- aiohttp: don't set global timeout

## [0.8.0] - 2022-07-02

### Added:

- switch from `requests` to `aiohttp`. Doing http requests asynchronously and in the case of pypi diagnostics, concurrently.
- diagnostic: lower severity of option redefined to same value to information level
- diagnostic: add hint level diagnostic for every redefined value
- cli: new `--log-pygls` flag to include pygls logs. By default they are not included.
- diagnostic: report unknown pypi projects or versions

### Fixed:

- pypi: fix a crash when unknown project is listed in `versions`
- diagnostic: don't emit false positives for profiles generated with jinja
- fix crash with empty `${buildout:extends}`

## [0.7.1] - 2022-05-08

### Added:

- recipe: support defining deprecated options
- recipe: support `slapos.recipe.template` version 0.5

### Fixed:

- recipe: fix some markdown syntax in recipe docs

## [0.7.0] - 2022-04-03

### Added:

- code actions: report progress when updating md5sum
- expose commands to start & stop profiling.

### Fixed:

- significantly improve performance by implementing .copy() method and using an intermediate cache.
- fix crash when completing option made only of space
- fix crash when completing after ${}

## [0.6.2] - 2022-01-06

### Fixed:

- fix a packaging mistake with the vscode extension

## [0.6.1] - 2022-01-04

### Fixed:

- fix problems with automatic publishing of packages

## [0.6.0] - 2022-01-04

### Added:

- diagnostic: report versions with known vulnerabilities
- code action: update a python package listed in `versions` to latest version
- code action: view a python package page on pypi
- code action: compute md5sum of an url

### Removed

- support for python 3.6, minimal supported version is now 3.7

### Fixed:

- completions: don't offer completions in comments
- ~~fix performance issues by cancelling pending tasks~~ actually the fix was wrong

## [0.5.0] - 2021-03-28

### Added:

- diagnostic: warn when options are redefining the current value
- completions: complete existing options of current sections
- diagnostic: support recipes with arbitrary options (like slapos.recipe.build)
- diagnostic: report error when existing non existant profiles

### Fixed:

- stop emitting false positives diagnostics with multi line jinja
- stop emitting false positives diagnostics for missing sections/options when extending dynamic profile
- fixed "add line comment" action

## [0.4.0] - 2020-10-08

### Fixed:

- don't skip lines containing jinja expressions. This was causing some missing options when jinja was used in option
- diagnostic: tolerate unknown part when extends jinja

## [0.3.0] - 2020-02-23

### Added:

- support http URLs in `${buildout:extends}`

## [0.2.1] - 2020-04-25

### Fixed

- references: consider listing a section in `${buildout:parts}` as a reference.
- completions: use `textEdit` to properly overwrite exiting text.
- all: debounce protocol functions to accept cancellations.
- all: fix errors when opening profiles outside of workspace.

## [0.2.0] - 2020-02-12

### Added:

- support running with buildout < 2.9.3
- initial support of `instance.cfg` defined using `slapos.recipe.template:jinja2`

### Fixed

- fixed broken v0.1.1 release, it could not be installed from pypi.
- diagnostics: prevent "missing required options" false positive on sections used only as macros.
- diagnostic: Correctly analyze sections with `.` or `-` in their names
- diagnostic: Fix false positives on `${buildout:parts}` with extended sections
- diagnostic: Fix false positives on `${buildout:parts}` when dynamically adding parts with jinja.

## [0.1.1] - 2020-01-30

### Added

- definitions: paths from `${buildout:extends}` can also be opened with jump to definition.
- completions: fix insertText with `-`.
- diagnostics: detect missing non existant sections listed in `${buildout:parts}`.
- diagnostics: detect sections without recipe listed in `${buildout:parts}`.

## 0.1.0 - 2020-01-04

- Initial Version

[keepachangelog]: https://keepachangelog.com/en/1.0.0/
[semver]: https://semver.org/spec/v2.0.0.html
[unreleased]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.9.3...main
[0.9.3]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.9.2...v0.9.3
[0.9.2]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.9.1...v0.9.2
[0.9.1]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.8.3...v0.9.0
[0.8.3]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.8.2...v0.8.3
[0.8.2]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.7.1...v0.8.0
[0.7.1]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.6.2...v0.7.0
[0.6.2]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.1.0...v0.1.1
