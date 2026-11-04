#!/bin/bash
# macOS built-ins only; compatible with Apple's Bash 3.2.
set -Eeuo pipefail
umask 077
export PATH=/usr/bin:/bin:/usr/sbin:/sbin

RESOURCES=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
STATE="$HOME/Library/Application Support/Growtopia Launcher"
LOG="$HOME/Library/Logs/Growtopia Launcher.log"
CURL=/usr/bin/curl
HDIUTIL=/usr/bin/hdiutil
DITTO=/usr/bin/ditto
CODESIGN=/usr/bin/codesign
XATTR=/usr/bin/xattr
PLISTBUDDY=/usr/libexec/PlistBuddy
OSASCRIPT=/usr/bin/osascript
OPEN=/usr/bin/open
UNAME=/usr/bin/uname
MODE=play
RUN_DIR=
WORK=
MOUNT=
STAGE=
LOCK_OWNED=0
ACTIVE_CHILD=
IN_COMMIT=0
TARGET=
SOURCE=cdn
TRUST=manual
REMOTE_DATE=
REMOTE_LENGTH=
REMOTE_ETAG=
DOWNLOAD_STATE=unknown
NEW_VERSION=
LAST_CHECK=

info_string() {
    local file=$1 key=$2 value=$3
    value=${value//\\/\\\\}
    value=${value//\"/\\\"}
    value=${value//$'\n'/ }
    value=${value//$'\r'/ }
    "$PLISTBUDDY" -c "Add :${key} string \"${value}\"" "$file" >/dev/null
}

write_info() {
    [[ -n "$RUN_DIR" && -d "$RUN_DIR" ]] || return 0
    local file="$RUN_DIR/info.tmp.plist" installed_version installed_build installed=false
    installed_version=$(plist_value "$TARGET" CFBundleShortVersionString || true)
    installed_build=$(plist_value "$TARGET" CFBundleVersion || true)
    [[ ! -d "$TARGET" ]] || installed=true
    printf '%s\n' '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"><plist version="1.0"><dict/></plist>' > "$file"
    info_string "$file" installedVersion "$installed_version"
    info_string "$file" installedBuild "$installed_build"
    info_string "$file" installed "$installed"
    info_string "$file" target "$TARGET"
    info_string "$file" source "$SOURCE"
    info_string "$file" trust "$TRUST"
    info_string "$file" remoteLastModified "$REMOTE_DATE"
    info_string "$file" remoteSizeBytes "$REMOTE_LENGTH"
    info_string "$file" remoteETag "$REMOTE_ETAG"
    info_string "$file" downloadState "$DOWNLOAD_STATE"
    info_string "$file" downloadedVersion "$NEW_VERSION"
    info_string "$file" lastDownloadedVersion "$(read_setting last-download-version)"
    info_string "$file" lastDownloadSource "$(read_setting last-download-source)"
    info_string "$file" lastCheck "$LAST_CHECK"
    mv -f "$file" "$RUN_DIR/info.plist"
}

progress() {
    [[ -n "$RUN_DIR" ]] || return 0
    printf '%s\n' "$1" > "$RUN_DIR/progress.tmp"
    mv -f "$RUN_DIR/progress.tmp" "$RUN_DIR/progress"
}

status() { printf '%s\n' "$*"; if [[ -n "$RUN_DIR" ]]; then printf '%s\n' "$*" > "$RUN_DIR/status.tmp"; mv -f "$RUN_DIR/status.tmp" "$RUN_DIR/status"; fi; }
fail() { printf '%s\n' "$*" >&2; if [[ -n "$RUN_DIR" ]]; then printf '%s\n' "$*" > "$RUN_DIR/error.txt"; fi; exit 1; }
cancel_check() { if [[ -f "$RUN_DIR/cancel" && "$IN_COMMIT" = 0 ]]; then status 'Stopped after the current safe step. Check the log for completed actions.'; exit 0; fi; }
read_setting() { if [[ -f "$STATE/$1" && ! -L "$STATE/$1" ]]; then /bin/cat "$STATE/$1"; fi; }
write_setting() { printf '%s\n' "$2" > "$STATE/$1.tmp"; mv -f "$STATE/$1.tmp" "$STATE/$1"; }
dialog() { "$OSASCRIPT" "$RESOURCES/dialogs.applescript" "$1" "$2"; }
plist_value() { "$PLISTBUDDY" -c "Print :$2" "$1/Contents/Info.plist" 2>/dev/null; }

cleanup() {
    local code=$?
    trap - EXIT ERR TERM INT
    set +e
    if [[ -n "$ACTIVE_CHILD" ]]; then kill "$ACTIVE_CHILD" 2>/dev/null; wait "$ACTIVE_CHILD" 2>/dev/null; fi
    if [[ -n "$MOUNT" ]]; then "$HDIUTIL" detach "$MOUNT" -quiet || "$HDIUTIL" detach "$MOUNT" -force -quiet; fi
    if [[ -n "$STAGE" && -d "$STAGE" ]]; then rm -rf "$STAGE"; fi
    if [[ -n "$WORK" && -d "$WORK" ]]; then rm -rf "$WORK"; fi
    if [[ "$LOCK_OWNED" = 1 ]]; then rm -f "$STATE/lock/pid"; rmdir "$STATE/lock" 2>/dev/null; fi
    if [[ -n "$RUN_DIR" && -d "$RUN_DIR" ]]; then
        if [[ "$code" != 0 && ! -s "$RUN_DIR/error.txt" ]]; then
            printf '%s\n' 'The update stopped before completion. Your installed game was kept unless the log reports a completed replacement. Open the log for details.' > "$RUN_DIR/error.txt"
        fi
        write_info || true
        if [[ "$code" = 0 ]]; then printf 'ok\n' > "$RUN_DIR/result.tmp"; else printf 'error\n' > "$RUN_DIR/result.tmp"; fi
        mv -f "$RUN_DIR/result.tmp" "$RUN_DIR/result"
    fi
    exit "$code"
}

acquire_lock() {
    if ! mkdir "$STATE/lock" 2>/dev/null; then
        local owner orphan_age=0 lock_time
        owner=$(cat "$STATE/lock/pid" 2>/dev/null || true)
        if [[ -z "$owner" ]]; then
            lock_time=$(/usr/bin/stat -f %m "$STATE/lock" 2>/dev/null || printf 0)
            [[ "$lock_time" =~ ^[0-9]+$ ]] || lock_time=0
            if [[ "$lock_time" -gt 0 ]]; then orphan_age=$(( $(date +%s) - lock_time )); fi
        fi
        if { [[ "$owner" =~ ^[0-9]+$ ]] && ! kill -0 "$owner" 2>/dev/null; } || { [[ -z "$owner" && "$orphan_age" -gt 30 ]]; }; then
            rm -f "$STATE/lock/pid"
            rmdir "$STATE/lock" 2>/dev/null || fail 'Cannot clear the old launcher lock. Open the log for details.'
            mkdir "$STATE/lock" 2>/dev/null || fail 'Another launcher is already checking for updates.'
        else
            fail 'Growtopia Launcher is already running. Close its other window and try again.'
        fi
    fi
    LOCK_OWNED=1
    printf '%s\n' "$$" > "$STATE/lock/pid"
}

validate_target() {
    # Only the two explicit game locations are ever replaced.
    case "$TARGET" in
        '/Applications/Growtopia.app'|"$HOME/Applications/Growtopia.app") ;;
        *) fail 'The saved game location is not supported. Remove the launcher target setting and run again.' ;;
    esac
    [[ ! -L "$TARGET" && ! -L "${TARGET%/*}" ]] || fail 'The game or its Applications folder is a symbolic link. Refusing to replace it.'
    mkdir -p "${TARGET%/*}"
    case "$MODE" in
        play|update|fresh|restore)
            [[ -w "${TARGET%/*}" ]] || fail "Cannot update $TARGET without administrator access. Choose Personal Applications in the launcher settings."
            ;;
    esac
}

choose_trust() {
    local answer
    answer=$(dialog setup "Choose how this launcher handles downloaded Growtopia builds.\n\nKeep macOS Checks: preserve quarantine and normal Gatekeeper prompts.\n\nTrust Official Downloads: allow this launcher to remove quarantine from Growtopia.app only, including future builds from the selected official HTTPS source. This can skip Apple's first-open/notarization check. It does not prove an unsigned build is safe.\n\nBroken signatures, unexpected bundle IDs, and changes to a pinned signing team are still rejected. No global security settings or login details are changed.") || exit 0
    if [[ "$answer" = 'Trust Official Downloads' ]]; then TRUST=official; else TRUST=manual; fi
    write_setting trust "$TRUST"
}

load_config() {
    TARGET=$(read_setting target)
    SOURCE=$(read_setting source)
    TRUST=$(read_setting trust)
    [[ "$SOURCE" = cdn || "$SOURCE" = website ]] || SOURCE=cdn
    LAST_CHECK=$(read_setting "$SOURCE.last-check")
    if [[ -z "$TARGET" ]]; then
        if [[ -d /Applications/Growtopia.app && ! -L /Applications/Growtopia.app && -w /Applications ]]; then
            TARGET=/Applications/Growtopia.app
        else
            TARGET="$HOME/Applications/Growtopia.app"
        fi
        write_setting target "$TARGET"
    fi
    validate_target
    if [[ "$TRUST" != official && "$TRUST" != manual ]]; then
        case "$MODE" in
            play|update|fresh|restore) choose_trust ;;
            *) TRUST=manual ;;
        esac
    fi
}

official_url() {
    # Recheck these exact first-party entry points; never accept a custom URL.
    if [[ "$SOURCE" = cdn ]]; then printf '%s' 'https://ubistatic-a.akamaihd.net/0098/01020126/Growtopia.dmg'; else printf '%s' 'https://growtopiagame.com/Growtopia-mac.dmg'; fi
}

allowed_url() {
    case "$1" in
        https://ubistatic-a.akamaihd.net/*|https://growtopiagame.com/*|https://www.growtopiagame.com/*) return 0 ;;
        *) return 1 ;;
    esac
}

header_value() {
    /usr/bin/awk -v key="$2" 'tolower($0) ~ "^" key ":" {sub(/^[^:]*:[ \t]*/, ""); sub(/\r$/, ""); value=$0} END {print value}' "$1"
}

probe_remote() {
    local code location count=0
    FETCH_URL="$(official_url)?gtlauncher=$(/bin/date +%s)"
    while :; do
        allowed_url "$FETCH_URL" || return 1
        code=$("$CURL" --disable --silent --show-error --head --proto '=https' --connect-timeout 12 --max-time 25 --max-filesize 1073741824 -H 'Cache-Control: no-cache' -H 'Pragma: no-cache' -D "$WORK/headers" -o /dev/null -w '%{http_code}' "$FETCH_URL") || return 1
        case "$code" in
            200) break ;;
            301|302|303|307|308)
                count=$((count + 1)); [[ "$count" -le 5 ]] || return 1
                location=$(header_value "$WORK/headers" location)
                if [[ "$location" = /* && "$location" != //* ]]; then
                    FETCH_URL="$(printf '%s' "$FETCH_URL" | /usr/bin/sed -E 's#^(https://[^/]+).*#\1#')$location"
                else FETCH_URL="$location"; fi
                ;;
            *) return 1 ;;
        esac
    done
    REMOTE_DATE=$(header_value "$WORK/headers" last-modified)
    REMOTE_LENGTH=$(header_value "$WORK/headers" content-length)
    REMOTE_ETAG=$(header_value "$WORK/headers" etag)
    [[ "$REMOTE_LENGTH" =~ ^[0-9]+$ ]] || REMOTE_LENGTH=
    [[ -z "$REMOTE_LENGTH" || "$REMOTE_LENGTH" -le 1073741824 ]] || return 1
    LAST_CHECK=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    write_setting "$SOURCE.last-check" "$LAST_CHECK"
}

download_dmg() {
    status 'Downloading official Growtopia DMG...'
    # Redirects were resolved and allowlisted by HEAD. Refuse changed redirects.
    "$CURL" --disable --fail --silent --show-error --proto '=https' --connect-timeout 15 --max-time 900 --retry 2 --retry-delay 2 --max-filesize 1073741824 -H 'Cache-Control: no-cache' -H 'Pragma: no-cache' -o "$WORK/Growtopia.dmg.part" -w '%{http_code}' "$FETCH_URL" > "$WORK/download-code" &
    ACTIVE_CHILD=$!
    while kill -0 "$ACTIVE_CHILD" 2>/dev/null; do
        if [[ -f "$RUN_DIR/cancel" ]]; then kill "$ACTIVE_CHILD" 2>/dev/null || true; wait "$ACTIVE_CHILD" 2>/dev/null || true; ACTIVE_CHILD=; cancel_check; fi
        local bytes
        bytes=$(/usr/bin/stat -f %z "$WORK/Growtopia.dmg.part" 2>/dev/null || printf 0)
        status "Downloading Growtopia: $((bytes / 1048576)) MB${REMOTE_LENGTH:+ of $(( ${REMOTE_LENGTH:-0} / 1048576 )) MB}"
        if [[ -n "$REMOTE_LENGTH" && "$REMOTE_LENGTH" -gt 0 ]]; then
            local percentage=$(( bytes * 100 / REMOTE_LENGTH ))
            [[ "$percentage" -le 100 ]] || percentage=100
            progress "$percentage"
        fi
        /bin/sleep 1
    done
    if ! wait "$ACTIVE_CHILD"; then ACTIVE_CHILD=; fail 'The download failed. Your installed game was kept. Check your connection or change the download source in Settings.'; fi
    ACTIVE_CHILD=
    [[ "$(cat "$WORK/download-code")" = 200 ]] || fail 'The download URL changed or returned an unexpected response. Your installed game was kept.'
    [[ -s "$WORK/Growtopia.dmg.part" ]] || fail 'The official server returned an empty download.'
    mv "$WORK/Growtopia.dmg.part" "$WORK/Growtopia.dmg"
    progress 100
}

fingerprint() {
    local app=$1 exe
    exe=$(plist_value "$app" CFBundleExecutable) || return 1
    [[ "$exe" != */* && -n "$exe" && "$exe" != . && "$exe" != .. ]] || return 1
    [[ -f "$app/Contents/MacOS/$exe" ]] || return 1
    { /usr/bin/shasum -a 256 "$app/Contents/Info.plist" | /usr/bin/awk '{print $1}'; /usr/bin/shasum -a 256 "$app/Contents/MacOS/$exe" | /usr/bin/awk '{print $1}'; } | /usr/bin/shasum -a 256 | /usr/bin/awk '{print $1}'
}

version_is_lower() {
    # Unknown/non-numeric metadata never becomes an invented game version.
    local version_pattern='^[0-9]+(\.[0-9]+)*$'
    [[ "$1" =~ $version_pattern && "$2" =~ $version_pattern ]] || return 1
    /usr/bin/awk -v a="$1" -v b="$2" 'BEGIN {na=split(a,aa,"."); nb=split(b,bb,"."); n=na>nb?na:nb; for(i=1;i<=n;i++){if(aa[i]+0<bb[i]+0)exit 0; if(aa[i]+0>bb[i]+0)exit 1} exit 1}'
}

running_game() {
    # No Accessibility/Automation permission and no broad process killing.
    local process_name
    process_name=$(plist_value "$TARGET" CFBundleExecutable || true)
    case "$process_name" in ''|*/*|-*) process_name=Growtopia ;; esac
    /usr/bin/pgrep -x "$process_name" >/dev/null 2>&1
}

launch_game() {
    cancel_check
    [[ -d "$TARGET" ]] || fail 'Growtopia is not installed yet.'
    status 'Opening Growtopia...'
    "$OPEN" "$TARGET" || fail "macOS could not open $TARGET. If normal macOS checks are enabled, review Privacy & Security, or choose the remembered trust option in Launcher Settings."
}

ensure_not_running() {
    if running_game; then
        case "$MODE" in
            update|fresh|restore) fail 'Growtopia is running. Quit the game, then try the update again.' ;;
        esac
        dialog running 'Growtopia is running. Close the game and open the launcher again to install updates. The running game will not be replaced.' >/dev/null || exit 0
        launch_game
        exit 0
    fi
}

cache_matches() {
    [[ -d "$TARGET" && ! -f "$STATE/force-fresh" ]] || return 1
    [[ -n "$REMOTE_DATE" && -n "$REMOTE_LENGTH" ]] || return 1
    [[ "$(read_setting "$SOURCE.date")" = "$REMOTE_DATE" && "$(read_setting "$SOURCE.length")" = "$REMOTE_LENGTH" && "$(read_setting "$SOURCE.etag")" = "$REMOTE_ETAG" ]] || return 1
    local fp
    fp=$(fingerprint "$TARGET") || return 1
    [[ -n "$fp" && "$fp" = "$(read_setting "$SOURCE.fingerprint")" ]]
}

inspect_app() {
    local app=$1 exe pinned_bundle pinned_team link link_target
    [[ -d "$app" && ! -L "$app" && -f "$app/Contents/Info.plist" && ! -L "$app/Contents/Info.plist" ]] || fail 'The disk image does not contain a regular Growtopia.app bundle.'
    /usr/bin/plutil -lint "$app/Contents/Info.plist" >/dev/null || fail 'Growtopia has an invalid Info.plist.'
    exe=$(plist_value "$app" CFBundleExecutable) || fail 'Growtopia has no executable metadata.'
    [[ -n "$exe" && "$exe" != */* && "$exe" != . && "$exe" != .. ]] || fail 'Growtopia contains an unsafe executable path.'
    [[ -f "$app/Contents/MacOS/$exe" && -x "$app/Contents/MacOS/$exe" && ! -L "$app/Contents/MacOS/$exe" ]] || fail 'The Growtopia executable is missing or is a symbolic link.'
    /usr/bin/file "$app/Contents/MacOS/$exe" | /usr/bin/grep -q 'Mach-O' || fail 'The downloaded Growtopia executable is not a macOS Mach-O binary.'
    # Never let an unsigned image point recursive operations outside its bundle.
    # Framework links such as Versions/Current are fine; parent/absolute links
    # are conservatively rejected, even if a future legitimate layout uses them.
    while IFS= read -r -d '' link; do
        link_target=$(/usr/bin/readlink "$link") || fail 'Cannot read a bundled symbolic link.'
        case "$link_target" in /*|..|../*|*/../*|*/..) fail 'Growtopia contains an absolute or parent-traversing symbolic link. The package layout needs review.' ;; esac
    done < <(/usr/bin/find "$app" -type l -print0)
    NEW_BUNDLE=$(plist_value "$app" CFBundleIdentifier) || fail 'Growtopia has no bundle identifier.'
    [[ "$NEW_BUNDLE" =~ ^[A-Za-z0-9._-]+$ ]] || fail 'Growtopia has an invalid bundle identifier.'
    NEW_VERSION=$(plist_value "$app" CFBundleShortVersionString || true)
    [[ -n "$NEW_VERSION" ]] || NEW_VERSION=$(plist_value "$app" CFBundleVersion || true)
    pinned_bundle=$(read_setting bundle-id)
    [[ -z "$pinned_bundle" || "$pinned_bundle" = "$NEW_BUNDLE" ]] || fail "The Growtopia bundle identifier changed from $pinned_bundle to $NEW_BUNDLE. Refusing this build."
    NEW_TEAM=
    if "$CODESIGN" -d --verbose=4 "$app" > "$WORK/signature" 2>&1; then
        "$CODESIGN" --verify --deep --strict --verbose=2 "$app" || fail 'Growtopia has a broken code signature. This build will not be installed, even with the trust option enabled.'
        NEW_TEAM=$(/usr/bin/sed -n 's/^TeamIdentifier=//p' "$WORK/signature" | /usr/bin/head -1)
        [[ "$NEW_TEAM" != 'not set' ]] || NEW_TEAM=
        if [[ -n "$NEW_TEAM" ]]; then
            # A self-signed or ad-hoc TeamIdentifier is not publisher identity.
            if ! "$CODESIGN" --verify --strict -R 'anchor apple generic and certificate 1[field.1.2.840.113635.100.6.2.6] exists and certificate leaf[field.1.2.840.113635.100.6.1.13] exists' "$app"; then NEW_TEAM=; fi
        fi
    else
        /usr/bin/grep -q 'code object is not signed at all' "$WORK/signature" || fail 'The code signature could not be inspected. Refusing this build.'
    fi
    pinned_team=$(read_setting team-id)
    [[ -z "$pinned_team" || "$pinned_team" = "$NEW_TEAM" ]] || fail 'The Growtopia signing team changed or disappeared. Refusing this build; the previous game was kept.'
    local old_version
    old_version=$(plist_value "$TARGET" CFBundleShortVersionString || true)
    if version_is_lower "$NEW_VERSION" "$old_version"; then fail "The official download reports version $NEW_VERSION, below your installed $old_version. Try the other official source in Settings; no downgrade was performed."; fi
}

apply_trust() {
    local app=$1
    if [[ "$TRUST" = official ]]; then
        # Recursive change is scoped to the staged bundle, never a whole folder.
        "$XATTR" -r -d com.apple.quarantine "$app" 2>/dev/null || {
            # No attribute is normal for curl/ditto output. Refuse real failures.
            if "$XATTR" -r "$app" 2>/dev/null | /usr/bin/grep -q com.apple.quarantine; then fail 'Could not apply the approved Growtopia-only trust setting.'; fi
        }
    else
        # curl normally omits quarantine. Re-add it to preserve the user's choice.
        "$XATTR" -w com.apple.quarantine "0083;$(printf '%x' "$(date +%s)");GrowtopiaLauncher;$(/usr/bin/uuidgen)" "$app" || fail 'Could not preserve macOS first-open checks. The download was not installed.'
    fi
}

commit_stage() {
    local backup="${TARGET%/*}/.Growtopia.previous.app" displaced="$WORK/older-backup.app" had_target=0
    [[ ! -L "$backup" ]] || fail 'The rollback location is a symbolic link. Refusing to overwrite it.'
    cancel_check
    ensure_not_running
    IN_COMMIT=1
    # Write-ahead journal permits recovery if power is lost between the renames.
    write_setting transaction-target "$TARGET"
    if [[ -e "$backup" ]]; then mv "$backup" "$displaced" || fail 'Could not rotate the previous backup. Your game was kept.'; fi
    if [[ -e "$TARGET" ]]; then
        if ! mv "$TARGET" "$backup"; then
            [[ ! -d "$displaced" ]] || mv "$displaced" "$backup" || true
            rm -f "$STATE/transaction-target"
            fail 'macOS refused to move the installed game. Your game was kept. A protected /Applications installation may require a manual permissions fix.'
        fi
        had_target=1
    fi
    if ! mv "$STAGE/Growtopia.app" "$TARGET"; then
        if [[ "$had_target" = 1 ]]; then mv "$backup" "$TARGET" || fail "Automatic restore failed. The previous app remains at $backup. Move it back to $TARGET."; fi
        [[ ! -d "$displaced" ]] || mv "$displaced" "$backup" || true
        rm -f "$STATE/transaction-target"
        fail 'The replacement failed. The installed game was restored.'
    fi
    rm -f "$STATE/transaction-target"
    IN_COMMIT=0
}

recover_transaction() {
    local journal backup
    journal=$(read_setting transaction-target)
    [[ -n "$journal" ]] || return 0
    [[ "$journal" = "$TARGET" ]] || fail 'An unfinished install points at a different game location. Open the log before continuing.'
    backup="${TARGET%/*}/.Growtopia.previous.app"
    if [[ ! -e "$TARGET" && -d "$backup" && ! -L "$backup" ]]; then mv "$backup" "$TARGET" || fail "Interrupted installation: restore $backup to $TARGET manually."; fi
    rm -f "$STATE/transaction-target"
}

remember_download() {
    write_setting bundle-id "$NEW_BUNDLE"
    write_setting last-download-version "$NEW_VERSION"
    write_setting last-download-source "$SOURCE"
    if [[ -n "$NEW_TEAM" ]]; then write_setting team-id "$NEW_TEAM"; fi
    write_setting "$SOURCE.date" "$REMOTE_DATE"
    write_setting "$SOURCE.length" "$REMOTE_LENGTH"
    write_setting "$SOURCE.etag" "$REMOTE_ETAG"
    write_setting "$SOURCE.fingerprint" "$(fingerprint "$TARGET")"
    /usr/bin/shasum -a 256 "$WORK/Growtopia.dmg" | /usr/bin/awk '{print $1}' > "$STATE/last-dmg-sha256"
    rm -f "$STATE/force-fresh"
    DOWNLOAD_STATE=downloaded
    write_info
}

finish_update() {
    write_info
    case "$MODE" in
        update|fresh) status 'Installation complete. Click Launch Installed to open Growtopia.' ;;
        *) launch_game ;;
    esac
}

inspect_remote() {
    cancel_check
    status 'Checking the official Growtopia download...'
    if ! probe_remote; then
        DOWNLOAD_STATE=unreachable
        write_info
        fail 'Could not reach the selected official download. Check your connection or switch download source.'
    fi
    if cache_matches; then DOWNLOAD_STATE=unchanged; else DOWNLOAD_STATE=changed; fi
    write_info
    status 'Download check complete. The online bundle version is only known after downloading the DMG.'
}

update_and_play() {
    ensure_not_running
    cancel_check
    status 'Checking the official Growtopia download...'
    if ! probe_remote; then
        DOWNLOAD_STATE=unreachable
        write_info
        case "$MODE" in update|fresh) fail 'Could not reach the official download. Try again or switch the download source.' ;; esac
        if [[ -d "$TARGET" ]]; then dialog offline 'Could not check the official download. Your installed game was kept. You can launch it now, or try the other official download source in Launcher Settings.' >/dev/null || exit 0; launch_game; return; fi
        fail 'Could not reach the official download. Try again or switch the source in Growtopia Launcher Settings.'
    fi
    cancel_check
    if cache_matches; then DOWNLOAD_STATE=unchanged; status 'Official download metadata is unchanged.'; finish_update; return; fi
    DOWNLOAD_STATE=changed
    write_info
    download_dmg
    rm -f "$RUN_DIR/progress"
    cancel_check
    status 'Verifying disk image integrity...'
    "$HDIUTIL" verify "$WORK/Growtopia.dmg" -quiet || fail 'The DMG integrity check failed. Your installed game was kept.'
    cancel_check
    mkdir "$WORK/mount"
    MOUNT="$WORK/mount"
    status 'Mounting the download read-only...'
    "$HDIUTIL" attach "$WORK/Growtopia.dmg" -readonly -nobrowse -noautoopen -mountpoint "$MOUNT" -quiet || fail 'macOS could not mount the downloaded DMG.'
    [[ -d "$MOUNT/Growtopia.app" && ! -L "$MOUNT/Growtopia.app" ]] || fail 'The official DMG layout changed: Growtopia.app was not found at its root. Your game was kept.'
    STAGE=$(mktemp -d "${TARGET%/*}/.growtopia-stage.XXXXXX")
    status 'Staging and validating Growtopia...'
    "$DITTO" --noqtn "$MOUNT/Growtopia.app" "$STAGE/Growtopia.app"
    inspect_app "$STAGE/Growtopia.app"
    cancel_check
    status "Downloaded bundle version: ${NEW_VERSION:-not provided}; signing team: ${NEW_TEAM:-not publisher-verified}."
    apply_trust "$STAGE/Growtopia.app"
    cancel_check
    status 'Installing Growtopia and keeping one previous version...'
    commit_stage
    remember_download
    finish_update
}

restore_previous() {
    local backup="${TARGET%/*}/.Growtopia.previous.app"
    [[ -d "$backup" && ! -L "$backup" ]] || fail 'There is no previous version to restore yet.'
    ensure_not_running
    dialog restore 'Restore the previous installed Growtopia version? The current version will become the rollback copy. The game server may refuse an older client. This will not launch a fresh update check.' >/dev/null || return 0
    STAGE=$(mktemp -d "${TARGET%/*}/.growtopia-stage.XXXXXX")
    "$DITTO" --noqtn "$backup" "$STAGE/Growtopia.app"
    # Rollback is explicitly requested; do not reject its lower version.
    local current="$TARGET" temp_version
    temp_version=$(plist_value "$backup" CFBundleShortVersionString || true)
    # Validate structure/signature against pins while bypassing only version order.
    TARGET="$STAGE/nonexistent.app"
    inspect_app "$STAGE/Growtopia.app"
    TARGET="$current"
    apply_trust "$STAGE/Growtopia.app"
    commit_stage
    rm -f "$STATE/cdn.fingerprint" "$STATE/website.fingerprint"
    launch_game
}

show_settings() {
    local answer choice version
    version=$(plist_value "$TARGET" CFBundleShortVersionString || true)
    answer=$(dialog settings "Installed bundle version: ${version:-not available}\nGame: $TARGET\nDownload source: $SOURCE\nTrust mode: $TRUST\n\nNormal launch checks HTTP Last-Modified, size and ETag, then downloads changed builds. These do not reveal the server's required game version. Use Force Fresh Download if the game still requests an update.") || return 0
    case "$answer" in
        'Download Source')
            choice=$(dialog source 'Choose one of the two official Mac download entry points. The launcher does not guess which one is newer. Changing the source forces a fresh download on next launch.') || return 0
            if [[ "$choice" = 'Website Beta' ]]; then SOURCE=website; else SOURCE=cdn; fi
            write_setting source "$SOURCE"; touch "$STATE/force-fresh"
            ;;
        More)
            choice=$(dialog more 'Choose an action:') || return 0
            case "$choice" in
                'Force Fresh Download') touch "$STATE/force-fresh"; update_and_play ;;
                'Change Trust Setting') choose_trust; touch "$STATE/force-fresh" ;;
                'Restore Previous Version') restore_previous ;;
                'Open Log') "$OPEN" -a TextEdit "$LOG" ;;
                'Open Game Folder') "$OPEN" "${TARGET%/*}" ;;
                'Use Personal Applications Folder')
                    TARGET="$HOME/Applications/Growtopia.app"
                    validate_target
                    write_setting target "$TARGET"
                    touch "$STATE/force-fresh"
                    ;;
            esac
            ;;
    esac
}

main() {
    MODE=${1:-play}; RUN_DIR=${2:-}
    case "$MODE" in
        play|settings|inspect|update|fresh|launch|restore|trust-official|trust-manual|source-cdn|source-website|personal-target) ;;
        *) printf 'Unknown launcher mode\n' >&2; exit 1 ;;
    esac
    [[ -n "$RUN_DIR" && -d "$RUN_DIR" && ! -L "$RUN_DIR" ]] || { printf 'Missing private run directory\n' >&2; exit 1; }
    trap cleanup EXIT
    trap 'exit 130' INT TERM
    trap 'printf "Launcher error at line %s (exit %s)\n" "$LINENO" "$?" >&2' ERR
    [[ "$("$UNAME" -s)" = Darwin ]] || fail 'This launcher requires macOS.'
    mkdir -p "$STATE" "$HOME/Library/Logs"
    [[ ! -L "$STATE" ]] || fail 'Launcher settings folder must not be a symbolic link.'
    acquire_lock
    WORK=$(mktemp -d "${TMPDIR:-/tmp/}gtlauncher.XXXXXX")
    printf '\nGrowtopia Launcher 2.0 - %s - %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$MODE"
    load_config
    recover_transaction
    write_info
    case "$MODE" in
        settings) show_settings ;;
        inspect) inspect_remote ;;
        update|play) update_and_play ;;
        fresh) touch "$STATE/force-fresh"; update_and_play ;;
        launch) launch_game ;;
        restore) restore_previous ;;
        trust-official) TRUST=official; write_setting trust "$TRUST"; touch "$STATE/force-fresh"; status 'Growtopia-only trust enabled.' ;;
        trust-manual) TRUST=manual; write_setting trust "$TRUST"; touch "$STATE/force-fresh"; status 'Normal macOS first-open checks enabled.' ;;
        source-cdn|source-website)
            SOURCE=${MODE#source-}; write_setting source "$SOURCE"; LAST_CHECK=$(read_setting "$SOURCE.last-check"); touch "$STATE/force-fresh"
            status 'Download source saved. Run Check for Updates or Install / Update next.'
            ;;
        personal-target)
            TARGET="$HOME/Applications/Growtopia.app"; validate_target; write_setting target "$TARGET"; touch "$STATE/force-fresh"
            status 'Game location set to your personal Applications folder.'
            ;;
    esac
}

if [[ "${BASH_SOURCE[0]}" = "$0" ]]; then main "$@"; fi
