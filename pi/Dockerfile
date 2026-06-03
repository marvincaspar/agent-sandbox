FROM mcr.microsoft.com/devcontainers/typescript-node:24-trixie AS base

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        git \
    && rm -rf /var/lib/apt/lists/*

# Install pi globally
RUN echo "ignore-scripts=true" > ~/.npmrc \
    && npm install -g "@earendil-works/pi-coding-agent@0.78.0"


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
    && chmod -R 1777 /pi-agent \
    && chmod a+w /etc/passwd \
    && echo "prefix=/pi-agent/npm-global" > /home/piuser/.npmrc \
    && echo "min-release-age=7" >> /home/piuser/.npmrc \
    && echo "ignore-scripts=true" >> /home/piuser/.npmrc \
    && echo "allow-git=none" >> /home/piuser/.npmrc

ENV HOME=/home/piuser
WORKDIR /home/piuser

# Install extensions
# https://pi.dev/packages/@sherif-fanous/pi-catppuccin
RUN pi install npm:@sherif-fanous/pi-catppuccin
# https://pi.dev/packages/context-mode
RUN pi install npm:context-mode
# https://pi.dev/packages/pi-subagents
RUN pi install npm:pi-subagents

RUN curl -LO "https://acli.atlassian.com/linux/latest/acli_linux_arm64/acli"
RUN chmod +x ./acli
RUN mv ./acli /usr/local/bin/acli

# Runtime installs must not reuse a cache populated during image build.
# Keep the cache in a separate path that starts empty for the runtime UID.
ENV NPM_CONFIG_CACHE=/home/piuser/.npm-cache

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

FROM base AS go

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        golang-1.26 \
    && rm -rf /var/lib/apt/lists/*

FROM base AS php8.4

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        php-8.4 \
    && rm -rf /var/lib/apt/lists/*

FROM base AS php8.5

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        php-8.5 php-dom php-mbstring php-xml php-xmlwriter php-simplexml php-curl php-intl php-xmlreader \
    && rm -rf /var/lib/apt/lists/*