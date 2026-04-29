# Changelog

All notable changes to Agent Remote Bridge will be documented in this file.

## [0.2.0] - 2026-04-30

### Changed

- Reclassified `write_remote_file` and `append_remote_file` as experimental tools.
- Added session TTL enforcement and closed-session rejection.
- Normalized remote path handling to block traversal-style escapes.
- Improved service and port diagnostics so unhealthy remote state is not always treated as execution failure.

### Added

- Governance and support documentation for contributors and users.
- Packaging and release metadata for PyPI-style distribution.
- Documentation validation script and expanded CI/release workflow coverage.
