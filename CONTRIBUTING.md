# Contributing

Use [Issues](https://github.com/raitnigol/growtopia-macos-autoupdater/issues) for reproducible bugs and focused feature requests. For a security-sensitive issue, read [SECURITY.md](SECURITY.md) before posting details publicly.

## Before changing behavior

- Check the managed paths, download-source allowlist, signature checks, rollback logic, and cancellation behavior affected by the change.
- Do not add credential logging, raw preference-file uploads, automatic deletion of unrelated files, or global Gatekeeper-disabling commands.
- Keep public labels and messages descriptive. Avoid slogans, promotional text, and claims that have not been tested.
- Do not bundle Growtopia's game files with the updater.

## Development checks

The worker uses macOS's Bash 3.2 and built-in tools. New shell code must remain compatible with that shell and avoid locale-sensitive unbraced variable boundaries.

From the repository root, run:

```bash
python3 -m unittest discover -s tests -v
node tests/test_ui_model.cjs
```

These are development dependencies; users of the built application do not need Python or Node. When an actual GNU Bash 3.2 executable is available, select it with `GROWTOPIA_TEST_BASH` for the portable checks.

Use the macOS build script and review its output as described in [release maintenance](docs/releasing.md). Tests that mock macOS commands do not replace a native UI and installation test.

For updater changes, test with isolated copies or fixtures. Do not use an unprotected working game installation to manufacture permission or replacement failures.

## Pull requests

Explain the failing action, expected result, resulting behavior, and checks performed. Include the launcher and macOS versions for a native reproduction. Keep fixes focused and preserve the user's existing game unless a replacement has been fully staged and validated.

For screenshots, follow the [capture checklist](docs/screenshots/README.md). Add actual image files before linking them in documentation.

## License

Contributions to this project's code and documentation are submitted under [The Unlicense](LICENSE). Do not contribute third-party game files, credentials, private logs, or other content you do not have the right to distribute.
