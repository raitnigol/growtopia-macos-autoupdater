# Testing and diagnostics

## Recorded manual result

A user confirmed that the launcher downloaded and installed Growtopia **5.61** over **3.82**, then opened the game successfully. The exact launcher build used for that report was not recorded. The old client was obtained from a third-party download. A successful replacement does not verify the old binary's authenticity or safety.

The environment information below comes from that user's supplied macOS crash report. The earlier crash report describes a failed startup, not a successful test of that earlier launcher build.

| Field | Reported value |
| --- | --- |
| Processor architecture | ARM64, native |
| Hardware model | `Mac16,8` |
| macOS version | `27.0.1` |
| macOS build | `26A434` |
| System Integrity Protection | Enabled in the supplied report |
| Confirmed game update | `3.82 → 5.61`, followed by game launch |

No serial number, hardware UUID, host name, crash reporter key, account name, or incident identifier is needed in the public test matrix.

Intel Macs and other macOS releases are build targets. They should not be marked manually tested until someone records an actual result.

## Test a release

Record the launcher version, macOS version/build, architecture, hardware model, selected download source, and trust preference before starting.

### Existing installation

1. Keep a separate copy of a known-working game if rollback matters.
2. Quit Growtopia.
3. Open the launcher and confirm the managed game path.
4. Run **Check for Updates**. Confirm that the UI remains responsive and no full DMG is downloaded by that action alone.
5. Run **Update & Play**.
6. Check that installation finishes, Growtopia opens, and the version inside the game is the expected one.
7. Confirm that the image is ejected and the updater's private temporary files are cleaned up.
8. Review the log for unexpected errors.

A second unchanged update should be able to skip the large download when the source provides usable metadata and the installed fingerprint matches.

### Reinstall

Use **Download Again**, then **Launch Installed**. This exercises downloading, validation, mounting, replacement, backup, and cleanup even when the game version remains the same. It does not prove an old-to-new upgrade.

### Older-to-newer update

Use a genuine older Mac client from a source you trust. Preserve a separate working copy first. A third-party download is not made trustworthy by testing it with this updater.

Install the older app at the exact managed game path, verify its version in-game, then quit it. Run **Update & Play** and record the actual version after the update. Replacing the old app changes the installation fingerprint and invalidates an otherwise matching cache.

**Restore Previous** can provide the older copy if that backup is actually older. A reinstall may have saved the same version. Only one automatic previous copy is retained.

### Failure and cancellation checks

For a development build, test a network failure, cancellation during a download, a running game, a protected destination, and rollback after a controlled failed replacement. Do not alter a user's real working installation to manufacture a failure. Automated tests use isolated paths and mocked commands for these cases.

## Collect environment information

In the native app, choose **Growtopia Launcher → Copy Diagnostics** from the macOS menu bar. Paste the report into the issue form after reviewing it.

The report contains a whitelist of fields: macOS version/build, processor architecture, hardware model, processor information, memory in GiB, launcher build, installed game bundle versions, source, trust mode, and game-location category. It excludes usernames, home-directory paths, serial numbers, raw logs, and login data.

The command-line wrapper is available from a source checkout:

```bash
/bin/bash scripts/diagnostics.sh
```

It prints to standard output by default and does not create a report file or change the game. Review the output before sharing it; saving it to a file is your choice.

If reporting from a downloaded release without a source checkout, the essential environment fields can also be read with:

```bash
sw_vers
uname -m
sysctl -n hw.model
```

Do not substitute a full `system_profiler` dump. It can include identifiers and unrelated information that are not needed to reproduce the problem.

## Automated checks

The source includes worker/install behavior tests and UI-logic checks. macOS-specific commands are mocked in the portable tests. These checks establish behavior under their test conditions; they do not prove that the native interface renders or that Gatekeeper behaves the same on every Mac.

The build workflow compiles the native launcher and assembles release artifacts on macOS runners. It is configured to run a native GUI startup smoke check and a Foundation Trash-operation smoke check. See the relevant GitHub Actions run for the outcome; this document does not treat a configured check as a passing result. A startup check is not a manual test of a real game installation. Keep those results separate.

## Screenshots

Use real captures from the tested Mac. Follow the [screenshot checklist](screenshots/README.md), review every image for private data, and record the launcher version shown. A screenshot of a finished window is not by itself proof of every installation step.
