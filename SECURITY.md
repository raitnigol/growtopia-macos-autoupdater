# Security

## Reporting a security issue

Do not post passwords, session tokens, cookies, secret keys, raw game preference files, or an unreviewed diagnostic dump in a public issue.

If GitHub offers **Report a vulnerability** on this repository's Security tab, use that private reporting option. Otherwise, ask the maintainer through the [profile](https://github.com/raitnigol) for an appropriate private reporting route before sharing sensitive details. No private reporting channel is assumed to be enabled.

An ordinary bug can be reported with the [bug report form](https://github.com/raitnigol/growtopia-macos-autoupdater/issues/new?template=bug_report.yml) using sanitized steps and relevant error excerpts.

## Updater boundaries

- The configured game downloads use official HTTPS entry points and an allowed-host policy.
- DMG integrity and application-layout checks do not, by themselves, establish publisher identity or absence of malware.
- Existing code signatures must validate. A publisher team is recorded only when the signature meets the required Apple Developer ID certificate requirements. Once recorded, a changed or missing team is refused.
- A first unsigned or ad-hoc-signed game download has no publisher identity to pin. Trust in its source remains an assumption.
- The optional Growtopia-only trust preference can remove quarantine from staged game updates. It does not disable Gatekeeper globally or establish that an unsigned binary is safe.
- The launcher does not store game account passwords, inject login credentials, edit the game's login HTML, or inspect game preference files.
- **Copy Diagnostics** copies only whitelisted environment/application fields. It excludes usernames, home paths, serial numbers, raw logs, and login data. Review any report before posting it.
- Installer cleanup is limited to explicitly selected matching DMG files and moves them to the Trash. It does not recursively clear Downloads, game preferences, saved sessions, or unrelated files.

The launcher is not Developer ID signed or notarized. An ad-hoc release signature is not an Apple-issued publisher identity or notarization.

## Supported versions

Use the latest published release when reporting a problem. There is no separate security-maintenance commitment for older versions. A macOS deployment target is not evidence that every OS/hardware combination has been tested.
