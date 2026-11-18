#!/usr/bin/env bash
set -euo pipefail

# Register the runtime UID in /etc/passwd before starting pi.
# getpwuid(3) must resolve the runtime UID; append directly
# since the runtime UID may differ from any pre-registered user.
if ! grep -q "^[^:]*:[^:]*:$(id -u):" /etc/passwd; then
    printf 'piuser:x:%d:%d:piuser:%s:/bin/sh\n' \
        "$(id -u)" "$(id -g)" "${HOME}" >> /etc/passwd
fi

# Install image-provided Pi packages into the host-mounted agent directory.
# Configured packages are skipped; Pi reconciles configured-but-missing files
# when it starts.
required_packages=(
    'npm:@sherif-fanous/pi-catppuccin'
    'npm:context-mode'
    'npm:pi-subagents'
    'npm:pi-powerline-footer'
    'git:github.com/jonjonrankin/pi-caveman'
    'git:github.com/DietrichGebert/ponytail'
)
settings_file="${PI_CODING_AGENT_DIR:-${HOME}/.pi/agent}/settings.json"

for package in "${required_packages[@]}"; do
    if [[ ! -f "${settings_file}" ]] || ! grep -Fq "\"${package}\"" "${settings_file}"; then
        echo "Installing Pi package: ${package}" >&2
        pi install "${package}"
    fi
done

# Pass through to a shell when invoked via `pi:shell`; otherwise run pi.
case "${1:-}" in
    bash|sh) exec "$@" ;;
    *) exec pi "$@" ;;
esac
