#!/bin/bash
# Run the app's whitelisted diagnostics from a source checkout.
set -euo pipefail
source_root=$(CDPATH= cd -P -- "$(/usr/bin/dirname "${BASH_SOURCE[0]}")/.." && pwd)
exec /bin/bash "$source_root/Resources/diagnostics.sh" "$@"
