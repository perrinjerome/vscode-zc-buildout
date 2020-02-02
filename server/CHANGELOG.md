# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog][keepachangelog],
and this project adheres to [Semantic Versioning][semver].

## [Unreleased]

### Fixed

- fixed broken v0.1.1 release, it could not be installed from pypi.

## [0.1.1]

### Added

- definitions: paths from `${buildout:extends}` can also be opened with jump to definition.
- completions: fix insertText with `-`.
- diagnostics: detect missing non existant sections listed in `${buildout:parts}`.
- diagnostics: detect sections without recipe listed in `${buildout:parts}`.

## 0.1.0

- Initial Version

[keepachangelog]: https://keepachangelog.com/en/1.0.0/
[semver]: https://semver.org/spec/v2.0.0.html
[0.1.1]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.1.0...v0.1.1
[unreleased]: https://github.com/perrinjerome/vscode-zc-buildout/compare/v0.1.1...HEAD
