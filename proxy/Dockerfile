FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tinyproxy \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY tinyproxy.conf /etc/tinyproxy/tinyproxy.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8888

HEALTHCHECK --interval=2s --timeout=3s --start-period=5s --retries=5 \
    CMD nc -z localhost 8888

ENTRYPOINT ["/entrypoint.sh"]
