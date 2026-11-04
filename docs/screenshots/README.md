# Documentation screenshots

Screenshots are added from actual macOS captures. None are included yet. Do not create simulated installation screens or present an illustration as a tested result.

## Capture list

| File | Capture |
| --- | --- |
| `01-launcher-before-update.png` | Main window showing the installed game version and selected source before an update. |
| `02-first-open-approval.png` | The relevant macOS first-open approval, if shown. Crop to the launcher entry and required controls. |
| `03-launcher-installed.png` | Launcher installation complete, or the launcher in the personal Applications folder. |
| `04-download-progress.png` | A real download in progress with the current stage visible. |
| `05-update-complete.png` | The launcher after installation. Use a separate game screenshot to document the actual in-game version when relevant. |
| `06-preferences.png` | Source and trust controls with a clear caption stating the selected settings. |
| `07-remove-installers.png` | The explicit installer selection or removal confirmation, without unrelated Downloads contents. |

Only add links to these images once the files exist. Until then, the written installation guide is complete without image placeholders.

## Capture and editing

1. Use macOS's screenshot controls, such as **Shift–Command–5**, and capture the relevant window or selected area.
2. Keep text readable at the documentation's displayed size. Retain enough surrounding UI to show which app or settings page is open.
3. Close unrelated windows. Review every capture for passwords, session tokens, email addresses, account names, private paths, serial numbers, notifications, and unrelated files.
4. Crop or apply opaque redaction where necessary. Do not blur a password and assume it is unrecoverable.
5. Use short numbered callouts only when they explain a specific step. Keep the original controls and messages intact.
6. Save PNG files and use descriptive Markdown alt text and a short factual caption.

Do not alter version numbers, progress values, error text, or the successful/failed state of an installation. Do not include the game's login credentials or a signed-in account page.

Record the launcher version and macOS version used for a screenshot set. A screenshot from one version should not silently be reused as proof that another version was tested.
