# Getting newest sha256 digest for cgr.dev/chainguard/node:latest-dev on 2025-05-08:
# $ docker buildx imagetools inspect cgr.dev/chainguard/node:latest-dev
FROM cgr.dev/chainguard/node:latest-dev@sha256:704e0edd9d3e701c09afabafa31a6ecc594876c1e63046c1715f71435119df50 AS base

USER root
RUN apk add --no-cache \
        curl \
        ca-certificates \
        git

# Install pi globally
RUN echo "ignore-scripts=true" > ~/.npmrc
RUN npm add -g "@earendil-works/pi-coding-agent"

# Prepend extension binaries (host-mounted via /pi-agent). Security: binaries
# here can shadow any command; no privilege escalation (--cap-drop=ALL,
# --no-new-privileges), but review ~/.pi/agent/npm-global/bin/ after installs.
ENV PATH="/pi-agent/npm-global/bin:${PATH}"

# /home/piuser: world-writable (1777) so any runtime UID can write here.
#   read mounts inside it (700 would block a non-matching UID).
# /etc/passwd: world-writable so the entrypoint can add the runtime UID.
# .npmrc sets prefix=/pi-agent/npm-global so extensions persist across restarts.
# Written as a literal file because ENV HOME is not yet set to /home/piuser.
RUN mkdir -p /home/piuser \
    && chmod 1777 /home/piuser \
    && chmod a+w /etc/passwd \
    && echo "prefix=/pi-agent/npm-global" > /home/piuser/.npmrc

ENV HOME=/home/piuser
WORKDIR /home/piuser

# Register the runtime UID in /etc/passwd before starting pi.
# getpwuid(3) must resolve the runtime UID; nss_wrapper is
# unavailable in Wolfi so we append directly.
RUN <<'EOF'
cat > /usr/local/bin/entrypoint.sh << 'ENTRYPOINT'
#!/bin/sh
set -e

if ! grep -q "^[^:]*:[^:]*:$(id -u):" /etc/passwd; then
    printf 'piuser:x:%d:%d:piuser:%s:/bin/sh\n' \
        "$(id -u)" "$(id -g)" "${HOME}" >> /etc/passwd
fi

# Pass through to a shell when invoked via `pi:shell`; otherwise run pi.
case "${1:-}" in
    bash|sh) exec "$@" ;;
    *) exec pi "$@" ;;
esac
ENTRYPOINT
chmod +x /usr/local/bin/entrypoint.sh
EOF

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

FROM base AS go

USER root
RUN apk add --no-cache go-1.26

FROM base AS php8.4

USER root
RUN apk add --no-cache php-8.4

FROM base AS php8.5

USER root
RUN apk add --no-cache php-8.5