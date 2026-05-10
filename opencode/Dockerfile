# Getting newest sha256 digest for cgr.dev/chainguard/node:latest-dev on 2025-05-08:
# $ docker buildx imagetools inspect cgr.dev/chainguard/node:latest-dev
FROM cgr.dev/chainguard/node:latest-dev@sha256:704e0edd9d3e701c09afabafa31a6ecc594876c1e63046c1715f71435119df50 AS base

USER root
RUN apk add --no-cache \
        curl \
        ca-certificates \
        git

# Install opencode globally
RUN echo "ignore-scripts=true" > ~/.npmrc \
    && npm i -g opencode-ai@1.14.48

# /home/opencodeuser: world-writable (1777) so any runtime UID can write here.
#   read mounts inside it (700 would block a non-matching UID).
# /etc/passwd: world-writable so the entrypoint can add the runtime UID.
# .npmrc sets prefix=/opencode-agent/npm-global so extensions persist across restarts.
# Written as a literal file because ENV HOME is not yet set to /home/opencodeuser.
RUN mkdir -p /home/opencodeuser \
    && chmod 1777 /home/opencodeuser \
    && chmod a+w /etc/passwd

ENV HOME=/home/opencodeuser
WORKDIR /home/opencodeuser

# Register the runtime UID in /etc/passwd before starting opencode.
# getpwuid(3) must resolve the runtime UID; nss_wrapper is
# unavailable in Wolfi so we append directly.
RUN <<'EOF'
cat > /usr/local/bin/entrypoint.sh << 'ENTRYPOINT'
#!/bin/sh
set -e

if ! grep -q "^[^:]*:[^:]*:$(id -u):" /etc/passwd; then
    printf 'opencodeuser:x:%d:%d:opencodeuser:%s:/bin/sh\n' \
        "$(id -u)" "$(id -g)" "${HOME}" >> /etc/passwd
fi

# Pass through to a shell when invoked via `opencode:shell`; otherwise run opencode.
case "${1:-}" in
    bash|sh) exec "$@" ;;
    *) exec opencode "$@" ;;
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