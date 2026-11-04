#!/bin/bash
# Copy the already-open launcher into the user's Applications folder.
set -Eeuo pipefail
umask 077
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
SOURCE_APP=${1:-}
RUN_DIR=${2:-}
DEST_DIR="$HOME/Applications"
DEST_APP="$DEST_DIR/Growtopia Launcher.app"
STAGE=
OLD_MOVED=0
NEW_MOVED=0
IN_COMMIT=0
fail(){ printf '%s\n' "$*" >&2; printf '%s\n' "$*" > "$RUN_DIR/error.txt"; exit 1; }
status(){ printf '%s\n' "$*"; printf '%s\n' "$*" > "$RUN_DIR/status.tmp"; mv "$RUN_DIR/status.tmp" "$RUN_DIR/status"; }
cleanup(){
    local result=$?
    trap - EXIT ERR INT TERM
    set +e
    if [[ "$result" != 0 && "$OLD_MOVED" = 1 && "$NEW_MOVED" = 0 && ! -e "$DEST_APP" ]]; then
        mv "$STAGE/previous.app" "$DEST_APP" || printf 'Previous launcher preserved at %s\n' "$STAGE/previous.app" >> "$RUN_DIR/error.txt"
    fi
    if [[ -n "$STAGE" && -d "$STAGE" ]]; then
        if [[ "$result" != 0 && -d "$STAGE/previous.app" ]]; then
            printf 'Recovery folder: %s\n' "$STAGE" >> "$RUN_DIR/error.txt"
        else rm -rf "$STAGE"; fi
    fi
    if [[ "$result" != 0 && ! -s "$RUN_DIR/error.txt" ]]; then printf 'Launcher installation failed. Open the log for details.\n' > "$RUN_DIR/error.txt"; fi
    if [[ "$result" = 0 ]]; then printf 'ok\n' > "$RUN_DIR/result.tmp"; else printf 'error\n' > "$RUN_DIR/result.tmp"; fi
    mv "$RUN_DIR/result.tmp" "$RUN_DIR/result"
    exit "$result"
}
[[ -n "$RUN_DIR" && -d "$RUN_DIR" && ! -L "$RUN_DIR" ]] || exit 1
trap cleanup EXIT
trap 'exit 130' INT TERM
[[ "$(/usr/bin/uname -s)" = Darwin ]] || fail 'This installer requires macOS.'
[[ -d "$SOURCE_APP" && ! -L "$SOURCE_APP" ]] || fail 'The complete source app bundle is missing.'
source_id=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$SOURCE_APP/Contents/Info.plist")
[[ "$source_id" = ee.nigol.growtopia.launcher ]] || fail 'The source app has an unexpected identity.'
[[ ! -L "$DEST_DIR" && ! -L "$DEST_APP" ]] || fail 'The destination is a symbolic link; no files were changed.'
mkdir -p "$DEST_DIR"
[[ "$SOURCE_APP" != "$DEST_APP" ]] || { status 'The launcher is already installed.'; exit 0; }
if [[ -e "$DEST_APP" ]]; then
    existing_id=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$DEST_APP/Contents/Info.plist" 2>/dev/null || true)
    [[ "$existing_id" = ee.nigol.growtopia.launcher ]] || fail 'A different app already uses the destination name. Move it elsewhere before installing.'
fi
STAGE=$(mktemp -d "$DEST_DIR/.growtopia-ui-install.XXXXXXXX")
status 'Copying launcher to your Applications folder...'
/usr/bin/ditto --noqtn "$SOURCE_APP" "$STAGE/new.app"
/usr/bin/plutil -lint "$STAGE/new.app/Contents/Info.plist" >/dev/null
[[ -x "$STAGE/new.app/Contents/MacOS/GrowtopiaLauncher" ]] || fail 'The launcher executable was not copied correctly.'
if [[ -f "$RUN_DIR/cancel" ]]; then status 'Launcher installation cancelled before replacement.'; exit 0; fi
IN_COMMIT=1
if [[ -e "$DEST_APP" ]]; then mv "$DEST_APP" "$STAGE/previous.app"; OLD_MOVED=1; fi
mv "$STAGE/new.app" "$DEST_APP"
NEW_MOVED=1
IN_COMMIT=0
status 'Launcher installed in your personal Applications folder.'
