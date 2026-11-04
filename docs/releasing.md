# Building and publishing a release

This page is for maintainers. Users should download a built application from [Releases](https://github.com/raitnigol/growtopia-macos-autoupdater/releases) and follow the [installation guide](installation.md).

## Prepare the source

1. Update `VERSION` to a new version number.
2. Add release notes under `docs/releases/vVERSION.md` using that number, and update instructions affected by the change.
3. Run the portable worker and UI-logic checks.
4. Build on macOS with the repository's build script.
5. Test the actual app on a Mac. Record the exact launcher version, macOS version/build, architecture, hardware model identifier, source, trust preference, and game versions before/after.
6. Review the source and release contents for credentials, private logs, developer machine paths, downloaded game files, and temporary build files.

The project includes the updater's source and app resources. It does not publish Growtopia's DMG or installed game.

## Local macOS build

From a source checkout, use the build script:

```bash
python3 scripts/build_macos.py
```

Read the script's output for the artifact paths. Build dependencies belong to the development environment; they are not required by users of a built release.

The app is built for both Apple Silicon and Intel with a macOS 11.0 deployment target. Release signing is ad-hoc unless a separate Developer ID signing/notarization process has explicitly been configured. Do not describe an ad-hoc signature as notarized or publisher-verified.

## GitHub workflow

The repository workflow runs checks and builds release artifacts. On a successful push to `main`, a new version can be published when its release tag does not already exist. Pull-request runs must not publish a release.

The release must target the source commit whose files were built. Publish the application ZIP and its checksum file together. Do not attach a binary built from a different working tree.

If the release tag already exists, use a new version for another release rather than silently replacing published assets. Inspect failed Actions jobs before retrying them.

## Release notes and test results

Describe concrete behavior changes and known limitations. Keep these distinct:

- Automated checks with mocked system commands.
- Build and packaging checks on a macOS runner.
- A recorded manual test of the native app and a real game installation.

Do not expand one user's successful Apple Silicon result into an Intel or all-macOS compatibility claim. Use exact values from an environment report and omit machine identifiers that are not needed for reproduction.

## Screenshots

Use real Mac screenshots supplied by a tester or captured during a real test. Follow [the screenshot checklist](screenshots/README.md). Do not add placeholder or generated images that appear to document an installation which did not occur.
