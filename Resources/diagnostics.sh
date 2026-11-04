#!/bin/bash
# Whitelisted environment information only. No login data, logs or identifiers.
set -euo pipefail
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
if [[ "$(/usr/bin/uname -s)" != Darwin ]]; then printf 'This diagnostic command requires macOS.\n' >&2; exit 1; fi
app=${1:-"$HOME/Applications/Growtopia Launcher.app"}
state="$HOME/Library/Application Support/Growtopia Launcher"
value(){ /usr/libexec/PlistBuddy -c "Print :$2" "$1/Contents/Info.plist" 2>/dev/null || true; }
version_value(){
    local v
    v=$(value "$1" "$2")
    if [[ "$v" =~ ^[A-Za-z0-9._+-]+$ && ${#v} -le 80 ]]; then printf '%s' "$v"; else printf 'not available'; fi
}
printf 'Growtopia macOS Auto-Updater diagnostics\n'
printf 'macOS: %s\n' "$(/usr/bin/sw_vers -productVersion)"
printf 'Build: %s\n' "$(/usr/bin/sw_vers -buildVersion)"
printf 'Architecture: %s\n' "$(/usr/bin/uname -m)"
printf 'Hardware model: %s\n' "$(/usr/sbin/sysctl -n hw.model)"
printf 'Processor: %s\n' "$(/usr/sbin/sysctl -n machdep.cpu.brand_string 2>/dev/null || printf 'not available')"
memory=$(/usr/sbin/sysctl -n hw.memsize)
printf 'Memory GiB: %s\n' "$((memory / 1073741824))"
printf 'Launcher version: %s\n' "$(version_value "$app" CFBundleShortVersionString)"
printf 'Launcher build: %s\n' "$(version_value "$app" CFBundleVersion)"
source=cdn; trust=manual
if [[ -f "$state/source" && ! -L "$state/source" ]]; then selected=$(cat "$state/source"); if [[ "$selected" = cdn || "$selected" = website ]]; then source=$selected; fi; fi
if [[ -f "$state/trust" && ! -L "$state/trust" ]]; then selected=$(cat "$state/trust"); if [[ "$selected" = official || "$selected" = manual ]]; then trust=$selected; fi; fi
printf 'Download source: %s\n' "$source"
printf 'Game trust mode: %s\n' "$trust"
target=
if [[ -f "$state/target" && ! -L "$state/target" ]]; then target=$(cat "$state/target"); fi
case "$target" in
    /Applications/Growtopia.app) location='system Applications' ;;
    "$HOME/Applications/Growtopia.app") location='personal Applications' ;;
    '')
        if [[ -d /Applications/Growtopia.app ]]; then target=/Applications/Growtopia.app;location='system Applications';else target="$HOME/Applications/Growtopia.app";location='personal Applications';fi
        ;;
    *) target=;location='unsupported setting' ;;
esac
printf 'Managed location: %s\n' "$location"
if [[ -n "$target" && -d "$target" && ! -L "$target" ]]; then
    printf 'Game bundle version: %s\n' "$(version_value "$target" CFBundleShortVersionString)"
    printf 'Game bundle build: %s\n' "$(version_value "$target" CFBundleVersion)"
else printf 'Game bundle version: not installed\n'; fi
printf 'Diagnostics omit usernames, serial numbers, home paths, login data and raw logs.\n'
