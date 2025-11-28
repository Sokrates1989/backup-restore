#!/bin/bash
set -euo pipefail

# Enable recursive globbing to match files in nested directories
shopt -s globstar nullglob

for file in python-dependency-management/**/*.sh; do
    # Skip if no files matched
    [ -f "$file" ] || continue

    # Convert CRLF to LF (fallback to sed if dos2unix fails)
    if ! dos2unix "$file" >/dev/null 2>&1; then
        sed -i 's/\r$//' "$file"
    fi

    # Strip UTF-8 BOM if present (EF BB BF)
    if [ "$(head -c 3 "$file" | od -An -tx1 | tr -d ' ')" = "efbbbf" ]; then
        tail -c +4 "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    fi

    chmod +x "$file"
done
