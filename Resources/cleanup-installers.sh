#!/bin/bash
# Explicit selection only; no recursive or filename-only automatic deletion.
set -Eeuo pipefail
umask 077
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
[[ $# -ge 2 ]] || exit 1
all_args=("$@")
last_index=$(($# - 1))
RUN_DIR=${all_args[$last_index]}
FILES=("${all_args[@]:0:$last_index}")
RESOURCES=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
[[ -d "$RUN_DIR" && ! -L "$RUN_DIR" ]] || exit 1
status(){ printf '%s\n' "$*"; printf '%s\n' "$*" > "$RUN_DIR/status.tmp"; mv "$RUN_DIR/status.tmp" "$RUN_DIR/status"; }
fail(){ printf '%s\n' "$*" >&2; printf '%s\n' "$*" > "$RUN_DIR/error.txt"; exit 1; }
finish(){
    local code=$?
    trap - EXIT INT TERM
    set +e
    if [[ "$code" != 0 && ! -s "$RUN_DIR/error.txt" ]]; then printf 'Installer cleanup stopped. Completed moves remain in Trash.\n' > "$RUN_DIR/error.txt"; fi
    if [[ "$code" = 0 ]]; then printf 'ok\n' > "$RUN_DIR/result.tmp"; else printf 'error\n' > "$RUN_DIR/result.tmp"; fi
    mv "$RUN_DIR/result.tmp" "$RUN_DIR/result"
    exit "$code"
}
trap finish EXIT
trap 'exit 130' INT TERM
[[ "$(/usr/bin/uname -s)" = Darwin ]] || fail 'This operation requires macOS.'
# Validate the entire selection before moving the first file.
for path in "${FILES[@]}"; do
    [[ "$path" = /* && -f "$path" && ! -L "$path" ]] || fail 'Select regular Growtopia DMG files, not folders or symbolic links.'
    name=${path##*/}
    case "$name" in [Gg][Rr][Oo][Ww][Tt][Oo][Pp][Ii][Aa]*.[Dd][Mm][Gg]) ;; *) fail 'Only files named Growtopia*.dmg can be moved by this action.' ;; esac
 done
moved=0
for path in "${FILES[@]}"; do
    if [[ -f "$RUN_DIR/cancel" ]]; then status "Cleanup stopped after $moved file(s). Completed moves remain in Trash."; exit 0; fi
    status "Moving selected installer $((moved + 1)) of ${#FILES[@]} to Trash..."
    "$RESOURCES/trash-file.sh" "$path" || fail "Could not move selected installer to Trash. $moved file(s) were already moved. Eject a mounted image if macOS reports it is in use."
    moved=$((moved + 1))
 done
status "Moved $moved installer file(s) to Trash."
