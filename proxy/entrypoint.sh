#!/bin/sh
set -e

ALLOWED_DOMAINS_FILE="${ALLOWED_DOMAINS_FILE:-/etc/tinyproxy/allowed_domains.txt}"
FILTER_FILE="/etc/tinyproxy/filter"

# Build tinyproxy regex filter from the allowed-domains list.
# Supports:
#   example.com       — exact hostname match
#   *.example.com     — hostname + all subdomains
#   # comment lines   — ignored
> "$FILTER_FILE"

if [ ! -f "$ALLOWED_DOMAINS_FILE" ]; then
    echo "WARNING: allowed-domains file not found at $ALLOWED_DOMAINS_FILE — all requests will be blocked." >&2
else
    while IFS= read -r line || [ -n "$line" ]; do
        # Strip leading/trailing whitespace
        domain=$(printf '%s' "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        # Skip blank lines and comments
        case "$domain" in
            ''|\#*) continue ;;
        esac

        # Escape dots for use in regex
        escaped=$(printf '%s' "$domain" | sed 's/\./\\./g')

        # Wildcard: *.example.com  →  ^(.*\.)?example\.com$
        case "$domain" in
            \*.*)
                base=$(printf '%s' "$escaped" | sed 's/^\\\*\\\.//')
                printf '^(.*\\.)?%s$\n' "$base" >> "$FILTER_FILE"
                ;;
            *)
                printf '^%s$\n' "$escaped" >> "$FILTER_FILE"
                ;;
        esac
    done < "$ALLOWED_DOMAINS_FILE"
fi

# tinyproxy drops to User tinyproxy — ensure it can read the filter
chmod 644 "$FILTER_FILE"

echo "Proxy filter loaded. Allowed patterns:" >&2
cat "$FILTER_FILE" >&2

exec tinyproxy -d -c /etc/tinyproxy/tinyproxy.conf
