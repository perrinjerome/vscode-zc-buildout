# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog][keepachangelog],
and this project adheres to [Semantic Versioning][semver].

## [Unreleased]

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
[0.1.1]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.1.0...v0.1.1
[0.2.0]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.1.1...v0.2.0
[unreleased]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.2.0...HEAD
