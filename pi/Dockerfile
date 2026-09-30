# Getting newest sha256 digest for cgr.dev/chainguard/node:latest-dev on 2025-05-08:
# $ docker buildx imagetools inspect cgr.dev/chainguard/node:latest-dev
FROM cgr.dev/chainguard/node:latest-dev@sha256:f3efcc097ff61373465af43cd173256de01ea297e583ddead9be49efcff823bb AS base

USER root
RUN apk add --no-cache \
        curl \
        ca-certificates \
        git

RUN npm install -g --ignore-scripts @earendil-works/pi-coding-agent@0.99.1


# Prepend extension binaries (host-mounted via /pi-agent). Security: binaries
# here can shadow any command; no privilege escalation (--cap-drop=ALL,
# --no-new-privileges), but review ~/.pi/agent/npm-global/bin/ after installs.
ENV PATH="/pi-agent/npm-global/bin:${PATH}"

# /home/piuser: world-writable (1777) so any runtime UID can write here.
#   read mounts inside it (700 would block a non-matching UID).
# /etc/passwd: world-writable so the entrypoint can add the runtime UID.
# .npmrc sets prefix=/pi-agent/npm-global so extensions persist across restarts.
# Written as a literal file because ENV HOME is not yet set to /home/piuser.
RUN mkdir -p \
        /home/piuser \
        /pi-agent/npm-global \
    && chmod 1777 /home/piuser \
    && chmod 0777 /pi-agent /pi-agent/npm-global \
    && chmod a+w /etc/passwd \
    && echo "prefix=/pi-agent/npm-global" > /home/piuser/.npmrc \
    && echo "min-release-age=7" >> /home/piuser/.npmrc \
    && echo "ignore-scripts=true" >> /home/piuser/.npmrc \
    && echo "allow-git=none" >> /home/piuser/.npmrc

ENV HOME=/home/piuser
# Use a throw-away build cache so root's npm runs during image build
# never pollute the runtime cache path /home/piuser/.npm-cache.
ENV NPM_CONFIG_CACHE=/tmp/npm-build-cache
WORKDIR /home/piuser

# Install global tools. Pi packages are declared by entrypoint.sh after the
# host's ~/.pi/agent directory has been mounted.
# https://pi.dev/packages/context-mode
RUN npm install -g context-mode
# https://github.com/alibaba/open-code-review
RUN npm install -g @alibaba-group/open-code-review

# Make all extension files/dirs writable so any runtime user can upgrade packages.
RUN chmod -R a+rwX /pi-agent/npm-global

# Switch to the runtime cache path (empty at start; owned by whoever runs first).
ENV NPM_CONFIG_CACHE=/home/piuser/.npm-cache

# Install Bun (recommended by context-mode for 3-5x sandbox execution speed)
RUN curl -fsSL https://bun.sh/install | bash \
    && ln -sf /home/piuser/.bun/bin/bun /usr/local/bin/bun

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


FROM base AS php8.4

USER root
RUN apk add --no-cache php-8.4


FROM base AS php8.5

USER root
RUN apk add --no-cache php-8.5
