# Troubleshooting

Before reporting a problem, note the launcher version shown in the window and the exact action that failed. Keep the error text.

## macOS blocks the first launch

The launcher is not Developer ID signed or notarized. Attempt to open the app once, then review **System Settings → Privacy & Security → Open Anyway** if you trust that release.

Do not apply global Gatekeeper-disabling commands. If macOS reports malware, the downloaded file is unexpected, or signature validation fails, keep the warning and investigate the file.

## The launcher quits before showing its window

A startup crash in version 2.0.0 was traced to `CALayer.setBackgroundColor` through the JXA bridge on the reported Apple Silicon Mac. Version 2.0.1 replaced those card backgrounds with native `NSBox`/`NSColor` controls; later releases retain the change.

Use the latest release. If the current version still crashes:

1. Click **Report** in the macOS crash dialog.
2. Keep **Exception Type**, **Termination Reason**, and **Thread 0 Crashed** or the indicated crashed thread's stack.
3. Review the end of `~/Library/Logs/Growtopia Launcher UI.log`.
4. Open a [bug report](https://github.com/raitnigol/growtopia-macos-autoupdater/issues/new?template=bug_report.yml) with the relevant details.

The report may name `osascript`: the launcher's native entry point uses Apple's built-in JXA runtime for the interface. That name alone does not identify the cause.

Review a crash report before posting it. Remove private paths or identifiers you do not want public. Do not attach account credentials, session data, or the contents of game preference files.

## The game still says “Update Required”

1. Quit Growtopia.
2. Click **Download Again** and let installation finish.
3. Click **Launch Installed**.
4. If the game is still old, choose the other download source and run **Update & Play**.
5. Compare the version inside the game with the version required by its server.

HTTP headers do not establish the online game version. Ubisoft's source may still serve an older payload, and the bundle metadata may differ from the version displayed in-game. The updater cannot supply a release that its configured sources are not publishing.

## “Growtopia is running”

Quit the game before updating. **Open Running Game** opens the existing process and does not replace its installation. The updater does not forcibly quit the game.

## Replacing `/Applications/Growtopia.app` fails

Click **Use Personal Folder**, then **Install & Play**. Future installations go to `~/Applications/Growtopia.app`. The original copy elsewhere remains in place.

Use the launcher's **Launch Installed** or **Update & Play** control to open the managed path. A Dock icon for an old game copy may still point elsewhere.

## The download fails or the source is unavailable

Check your internet connection and try the other source in the source menu. A source change takes effect on the next update action.

**Launch Installed** opens the managed game without contacting the download server. It cannot make an old client acceptable to the game server.

## A signature, bundle identifier, signing-team, or package-layout error appears

The updater stops before installing an unexplained payload. Click **Open Log** and keep the relevant error. Do not disable its validation checks to force the download through.

A legitimate publisher or package layout change may require an updater change. Include the selected source, exact error, launcher version, and a sanitized log excerpt in a bug report. Do not upload the entire game app or DMG as a repository issue attachment.

## A replacement fails

The updater stages a complete replacement before moving the installed game. If the final replacement fails, it attempts to restore the previous copy. A transaction journal allows a later run to recover an interrupted rename when the previous copy remains available.

Read the error before moving anything manually. If automatic restore failed, the error identifies the retained backup path. Disk failures and permissions can still require manual recovery.

## The launcher says it is already running

Close the other launcher window and wait for its operation to finish. After a crash, the updater normally clears a stale process lock on a later run. A lock without a recorded process may need a short delay before it can be treated as abandoned.

Do not delete the lock while another updater operation is active. If it persists, report the error and sanitized log rather than starting multiple copies.

## Cancel was pressed but an installation finished

Cancellation stops after a safe step. The final replacement is committed as a unit, so cancellation requested during that step can finish the replacement before stopping. Check the installed version and log to see which actions completed.

## A mounted image or temporary folder remains

Normal completion, failure, and handled cancellation clean up the updater's temporary download and mount. Force Quit, a power interruption, or an operating-system failure can interrupt cleanup.

Eject the leftover image in Finder if needed. Do not remove the current game, `.Growtopia.previous.app`, or the launcher's state folder as generic cleanup: those are intentional retained files.

## Old DMGs remain in Downloads

The updater's private download is cleaned up automatically. A file saved earlier by a browser belongs to that separate download. Click **Remove Installers**, select only the Growtopia DMGs you no longer need, and confirm moving them to the Trash. Do not select an older installer you are retaining for an upgrade test.

This does not clear game caches, preferences, saved sessions, or unrelated files.

## Login, remembered credentials, and the HTML login page

The launcher does not read game preference files, store GrowID passwords, inject login data, or modify the game's HTML login flow. Use Growtopia's own login and account controls. [Ubisoft's login FAQ](https://ubisoft-mobile.helpshift.com/hc/en/26-growtopia/faq/2187-how-do-i-log-in-to-growtopia-google-apple-id-or-grow-id/) says the game saves sign-in state for later sessions and may require sign-in again after inactivity.

No documented updater override for the authentication HTML or supported Mac credential-prefill interface has been established for this release. The updater leaves the authentication page unchanged. A local text field or file does not establish that its value is a password, usable session token, or supported prefill setting. Do not post such values in an issue.

## What to include in an issue

Use the [bug report form](https://github.com/raitnigol/growtopia-macos-autoupdater/issues/new?template=bug_report.yml). Include:

- Launcher version and download source.
- macOS version and build, processor architecture, and hardware model identifier.
- The button you pressed, what happened, and what you expected.
- Growtopia versions before and after, when relevant.
- Exact error and the relevant end of a sanitized updater or UI log.
- A screenshot only when it explains the failure and contains no credentials or other private data.

Use **Growtopia Launcher → Copy Diagnostics** in the macOS menu bar and paste the reviewed output into the issue form. The [diagnostics procedure](testing.md#collect-environment-information) lists the limited fields gathered and the command-line alternative. It does not establish that all listed hardware and OS combinations are supported.
