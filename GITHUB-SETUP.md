# GitHub setup status

Repository: https://github.com/raitnigol/growtopia-macos-autoupdater
Prepared source version: 2.1.0

This archive contains the complete repository source and release setup, not a built application release.

The GitHub connection can read the repository, but GitHub rejected both Git-data blob creation and README creation with HTTP403: Resource not accessible by integration. No source commit, tag, workflow run, or release was published. The original LICENSE remains the repository's only file.

Configure/reconnect the GitHub integration with access to this repository and the repository-content/workflow permissions needed for these writes. Then return to the conversation so the prepared source can be committed and the native Mac build/release run monitored. Do not paste personal access tokens into chat.

The existing Unlicense text is preserved. No Growtopia game files, account credentials, user logs, private crash reports, or fabricated screenshots are included.

## Prepared checks

- 44 worker/installer/cleanup tests passed using GNU Bash3.2 on Linux.
- 10 build/release safety tests passed.
- 6 UI logic checks passed.
- Mac native GUI/Trash smoke checks and native universal build are configured in GitHub Actions, but have not run for this source because repository writes are blocked.

The source documents the reported ARM64 Mac16,8 / macOS27.0.1(26A434) environment and successful Growtopia3.82-to-5.61 update. It does not claim that all hardware/OS targets have been manually tested.

## Source layout

The growtopia-macos-autoupdater directory contains README.md, LICENSE, Resources, Bootstrap, scripts, tests, docs and .github. Preserve the .github directory when copying source files; it contains the CI/release workflow and issue forms.

Once the source is committed to main, the workflow tests on Mac runners, builds and ad-hoc signs a universal app, checks its window startup, and publishes vVERSION with the appZIP, checksums and source-commit build metadata. An existing tag or release is not overwritten.

See docs/installation.md, docs/troubleshooting.md, docs/testing.md and docs/releasing.md. For future screenshots, use docs/screenshots/README.md. The application menu Copy Diagnostics collects only whitelisted environment fields, not login data or raw logs.
