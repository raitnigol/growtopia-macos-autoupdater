# Growtopia macOS Auto-Updater

A macOS application for downloading, installing, updating, and launching the Growtopia Mac client. It uses Growtopia's official download links, keeps one previous game version, and provides update progress and rollback controls.

[Download a release](https://github.com/raitnigol/growtopia-macos-autoupdater/releases) · [Installation guide](docs/installation.md) · [Troubleshooting](docs/troubleshooting.md) · [Report a problem](https://github.com/raitnigol/growtopia-macos-autoupdater/issues/new/choose)

## Requirements

- A Mac with Apple Silicon or an Intel processor.
- The application is built with a macOS 11.0 deployment target. This is a build target, not a claim that every macOS version has been tested.
- An internet connection for update checks and downloads.

No Homebrew, Xcode, Python, or Terminal installer is needed to use the release application.

## Install

1. Open [Releases](https://github.com/raitnigol/growtopia-macos-autoupdater/releases) and download the application ZIP asset.
2. Extract the ZIP in Finder and open **Growtopia Launcher.app**.
3. If macOS blocks it, attempt to open it once, then review **System Settings → Privacy & Security → Open Anyway**. Approve only a copy you chose to trust.
4. In the launcher, click **Install Launcher**. It copies the launcher into `~/Applications`.
5. Close the downloaded copy, open the installed copy, and add it to the Dock if wanted.
6. Close Growtopia, then click **Install & Play** or **Update & Play**.

The launcher is not Developer ID signed or notarized. Release builds can use a local ad-hoc signature; that does not establish publisher identity or Apple notarization. A first-open approval may be required for a new launcher build.

See the [full installation and usage guide](docs/installation.md) for the trust setting, file locations, and each control's behavior.

## Controls

| Control | Action |
| --- | --- |
| **Check for Updates** | Checks the selected official download's headers without downloading the full game. |
| **Install & Play / Update & Play** | Checks the source, downloads and installs when needed, then opens Growtopia. |
| **Launch Installed** | Opens the managed copy without an update check. |
| **Cancel** | Requests cancellation after a safe step. A replacement already being committed may finish. |
| **Download source** | Selects the in-game Ubisoft CDN or official website beta source. The next update requests a fresh download. |
| **Trust official downloads for Growtopia only** | Changes the Growtopia-specific quarantine preference after confirmation. |
| **Use Personal Folder** | Sets the game target to `~/Applications/Growtopia.app`; install it with the next update action. |
| **Restore Previous** | Restores and opens the saved previous game after confirmation. |
| **Download Again** | Forces a new download and installation without auto-launching. Use **Launch Installed** afterward. |
| **Remove Installers** | Opens a file chooser for explicit selection of Growtopia DMGs and moves the confirmed files to the Trash. |
| **Open Log / Game Folder / Guide** | Opens the log, managed game's parent folder, or bundled guide. |

## What is checked

The updater downloads from the two configured official HTTPS entry points. It verifies the DMG's integrity, checks the app layout and executable, rejects broken signatures, and checks a previously recorded bundle identifier and publisher signing team when available. It refuses an automatic downgrade when both reported bundle versions can be compared numerically.

The optional Growtopia-only trust setting removes quarantine from staged Growtopia updates. It does not disable Gatekeeper globally, prove an unsigned download is safe, or override all macOS protections.

HTTP headers do not provide a verified latest game version. The UI displays version metadata from an installed or downloaded bundle; that metadata may differ from the version shown inside Growtopia. An unchanged download can be skipped using saved headers and the managed app's fingerprint.

The project does not distribute Growtopia itself. Game files are downloaded separately from the selected official source.

## Testing

A user reported a successful update from **Growtopia 3.82 to 5.61**, followed by a successful game launch. The exact launcher build used for that test was not recorded. The older 3.82 client came from a third-party download; this result does not verify that old binary's authenticity or safety.

| Environment | Evidence |
| --- | --- |
| Apple Silicon, ARM64, model `Mac16,8` | Reported by the user's macOS crash report. |
| macOS `27.0.1`, build `26A434` | Values reported in that same report. |
| Growtopia `3.82 → 5.61` | User confirmed the download completed and 5.61 opened. |
| Linux development environment | Automated worker, installation, and UI-logic checks using mocked macOS commands. |
| Intel Macs and other macOS versions | Build targets; no manual result is recorded yet. |

These results are not a guarantee for every Mac or future Growtopia release. See [testing and diagnostics](docs/testing.md) for the test procedure and how to collect another environment report.

## Problems and contributions

Use the [bug report form](https://github.com/raitnigol/growtopia-macos-autoupdater/issues/new?template=bug_report.yml) for a failure. Include the launcher version, macOS version/build, processor architecture, steps to reproduce, and the relevant error. Use **Growtopia Launcher → Copy Diagnostics** in the macOS menu bar to copy the environment fields for an issue. The [troubleshooting guide](docs/troubleshooting.md) explains where logs are saved.

Do not post passwords, tokens, session cookies, private account data, or an unreviewed full system report. See [SECURITY.md](SECURITY.md) for security-sensitive reports and [CONTRIBUTING.md](CONTRIBUTING.md) for development changes.

Installation screenshots will be added from actual macOS captures. The [screenshot checklist](docs/screenshots/README.md) lists the required views; no simulated screenshots are presented as evidence.

## License

The updater's source code is released under [The Unlicense](LICENSE). Growtopia, Ubisoft names, and downloaded game files are not covered by this project's license. This is an independent project and is not affiliated with or endorsed by Ubisoft.
