# Getting newest sha256 digest for cgr.dev/chainguard/node:latest-dev on 2025-05-08:
# $ docker buildx imagetools inspect cgr.dev/chainguard/node:latest-dev
FROM cgr.dev/chainguard/node:latest-dev@sha256:df7376d245b4a242d38e9289d265e6124a21217dea665001a0058960367fae46 AS base

USER root
RUN apk add --no-cache \
        curl \
        ca-certificates \
        git

# The install script hardcodes INSTALL_DIR=$HOME/.opencode/bin with no override.
# During the build HOME=/root, so we move the binary to /usr/local/bin afterwards.
RUN curl -fsSL https://opencode.ai/install | bash \
    && mv /root/.opencode/bin/opencode /usr/local/bin/opencode

# /home/opencodeuser: world-writable (1777) so any runtime UID can write here.
#   read mounts inside it (700 would block a non-matching UID).
# /etc/passwd: world-writable so the entrypoint can add the runtime UID.
RUN mkdir -p /home/opencodeuser \
    && chmod 1777 /home/opencodeuser \
    && chmod a+w /etc/passwd

ENV HOME=/home/opencodeuser
WORKDIR /home/opencodeuser

RUN ARCH="$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')" \
    && curl -fsSL "https://acli.atlassian.com/linux/latest/acli_linux_${ARCH}/acli" \
        -o /usr/local/bin/acli \
    && chmod +x /usr/local/bin/acli

RUN cat >/usr/local/bin/fake-browser <<'EOF'
#!/usr/bin/env bash
echo "${1}" >>/tmp/fake-browser.log
EOF

RUN chmod +x /usr/local/bin/fake-browser

RUN ln -f -s /usr/local/bin/fake-browser /usr/local/bin/www-browser
RUN ln -f -s /usr/local/bin/fake-browser /usr/local/bin/x-www-browser
RUN ln -f -s /usr/local/bin/fake-browser /usr/local/bin/xdg-open

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]


FROM base AS go

USER root
RUN apk add --no-cache go-1.26


FROM base AS php8.5

USER root
RUN apk add --no-cache \
        php-8.5 \
        php-8.5-ctype \
        php-8.5-dom \
        php-8.5-mbstring \
        php-8.5-openssl \
        php-8.5-phar \
        php-8.5-pdo \
        php-8.5-pdo_mysql \
        php-8.5-xmlwriter
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer
