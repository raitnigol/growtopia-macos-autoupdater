# Installation and usage

## 1. Download and extract

1. Open the project's [Releases page](https://github.com/raitnigol/growtopia-macos-autoupdater/releases).
2. Download the application ZIP asset for the release you want to use. Do not use GitHub's automatically generated **Source code** ZIP as the application installer.
3. In Finder, open Downloads and double-click the downloaded ZIP.
4. Open the extracted folder. It contains **Growtopia Launcher.app** and the bundled guide.

If a release provides `SHA256SUMS`, it can be used to check that the download matches that release's published checksum. A checksum is an integrity check, not an Apple signature or notarization.

## 2. Open the launcher

Double-click **Growtopia Launcher.app**.

The launcher is not Developer ID signed or notarized. If macOS blocks the first launch, attempt to open it once, then go to **System Settings → Privacy & Security** and review **Open Anyway**. Authenticate if macOS requests it. This approval concerns the launcher itself and is separate from the game's trust preference.

Do not disable Gatekeeper globally. A malware-detection warning, signature validation failure, or an unexpected file should be investigated rather than treated as a routine first-open prompt.

## 3. Install the launcher in your Applications folder

1. Click **Install Launcher** in the upper-right corner.
2. Wait for the copy to finish. The destination is `~/Applications/Growtopia Launcher.app`.
3. Click **Show Applications** when offered.
4. Close the downloaded copy and open the installed one.
5. Drag the installed launcher to the Dock if you want a persistent shortcut.

Finder's ordinary Applications sidebar entry may point at `/Applications`. To open your personal folder, press **Shift–Command–G**, enter `~/Applications`, and press Return.

The launcher replaces an existing launcher with its expected bundle identity. It refuses a different app that happens to have the same destination name. You can also run the launcher directly from the extracted folder; copying it gives its Dock shortcut a stable location.

## 4. Select the game trust preference

**Trust official downloads for Growtopia only** is unchecked by default when no previous preference exists.

| Setting | Behavior |
| --- | --- |
| Unchecked | Adds quarantine to staged game downloads so normal macOS first-open checks remain. An unnotarized Growtopia build may still require Open Anyway. |
| Checked | After confirmation, remembers permission to remove quarantine from staged Growtopia updates downloaded from the selected official source. This can skip repeated first-open/notarization prompts. |

This setting does not verify an unsigned game's publisher, disable Gatekeeper globally, or bypass a broken signature. A previously recorded bundle identifier and verified publisher signing team must still match.

The saved setting applies to subsequent installations. Changing it requests a fresh download; it does not immediately rewrite the already installed game.

## 5. Install or update Growtopia

1. Quit Growtopia completely.
2. Click **Install & Play**, or **Update & Play** when the managed game is already installed.
3. Leave the window open while the operation finishes. The status area shows the current step, with download percentage when a size is available.
4. Growtopia opens after a successful update-and-play operation.
5. Use the game's own login flow normally. [Ubisoft's login guide](https://ubisoft-mobile.helpshift.com/hc/en/26-growtopia/faq/2187-how-do-i-log-in-to-growtopia-google-apple-id-or-grow-id/) describes saved sign-in state for later sessions; sign-in can be required again after inactivity.

The first managed update downloads the full DMG even when Growtopia was already installed. Later updates can skip an unchanged download when the saved headers and installed app fingerprint match.

If a writable `/Applications/Growtopia.app` already exists, the updater normally uses it. Otherwise it uses `~/Applications/Growtopia.app`. The selected path is shown beside **Game folder**. An app at a different path is not automatically removed.

The updater keeps one previous game copy. It does not replace a running game. If a download check fails and the managed game exists, **Update & Play** can offer to launch that installed copy.

## 6. Daily use

Open the installed launcher and click **Update & Play**. Opening Growtopia directly skips the launcher's update check. The launcher does not install a background service or scheduled update task.

The window remains available after the game opens. Use **Growtopia Launcher → Copy Diagnostics** in the macOS menu bar to copy the limited environment report if a problem needs an issue. Use **Cancel** to request cancellation during an operation. Cancellation waits for a safe step; a replacement already being committed can finish. The log records completed actions.

## Download sources and versions

The source menu provides:

- **In-game Ubisoft CDN:** `https://ubistatic-a.akamaihd.net/0098/01020126/Growtopia.dmg`
- **Official website beta:** `https://growtopiagame.com/Growtopia-mac.dmg`

Changing the source saves the choice and requests a fresh download on the next installation action. It does not start downloading immediately.

**Check for Updates** checks HTTP metadata only. The resulting status does not prove that the download contains a newer client. The actual bundle version is read after downloading, and may differ from the version displayed inside Growtopia. Either official endpoint may temporarily publish a client older than the game server requires.

## Reinstall and rollback

**Download Again** downloads and installs the selected source again, even when its HTTP metadata matches. It does not auto-launch; use **Launch Installed** afterward.

**Restore Previous** validates the saved previous copy, asks for confirmation, restores it, and opens it without first checking for updates. The restored version may be rejected by the game server. A previous copy exists only after a managed replacement has created one, and it may be the same version after a reinstall.

Only one automatic previous game is retained. A later installation replaces that backup. Keep a separate copy if you need a particular known-working version for a test.

## Files and cleanup

| Item | Location |
| --- | --- |
| Launcher | `~/Applications/Growtopia Launcher.app` |
| Managed game | The **Game folder** path shown in the launcher |
| Previous game | `.Growtopia.previous.app`, a hidden sibling of the managed game |
| Updater settings | `~/Library/Application Support/Growtopia Launcher/` |
| Update log | `~/Library/Logs/Growtopia Launcher.log` |
| Interface/startup log | `~/Library/Logs/Growtopia Launcher UI.log` |

The updater's private temporary DMG, mount point, and staging files are cleaned up on normal completion, failure, and handled cancellation. The current game, one previous version, settings, and logs are intentional retained files. A forcibly killed process can leave an image or temporary folder behind.

An old browser-downloaded `Growtopia.dmg` in Downloads is separate from the updater's private download. Use **Remove Installers** to select the Growtopia DMGs you want removed. After confirmation, matching regular files are moved to the macOS Trash. The action does not recursively scan Downloads, remove unrelated files, or clear game preferences or login data. A previous installer you still need for a test should be left unselected.

## Remove the launcher

Quit the launcher and move `~/Applications/Growtopia Launcher.app` to the Trash. If an older separate **Growtopia Launcher Settings.app** is still present, it can also be removed. There is no background agent to disable.

The game, previous-game backup, settings, and logs are left in place unless you remove them separately. Do not remove the game if you only want to remove this helper.
