#!/bin/bash
set -euo pipefail
RESOURCES=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
exec /usr/bin/osascript -l JavaScript "$RESOURCES/trash-file.js" "$@"
