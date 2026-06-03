#!/bin/sh
set -e

# Register the runtime UID in /etc/passwd before starting pi.
# getpwuid(3) must resolve the runtime UID; append directly
# since the runtime UID may differ from any pre-registered user.
if ! grep -q "^[^:]*:[^:]*:$(id -u):" /etc/passwd; then
    printf 'piuser:x:%d:%d:piuser:%s:/bin/sh\n' \
        "$(id -u)" "$(id -g)" "${HOME}" >> /etc/passwd
fi

# Pass through to a shell when invoked via `pi:shell`; otherwise run pi.
case "${1:-}" in
    bash|sh) exec "$@" ;;
    *) exec pi "$@" ;;
esac