# Agent Sandbox

Runs AI coding agents inside isolated Docker containers. Agents get no root access, no Docker socket, and no ability to escalate privileges — safe to run on your host machine.

---

## Agents

### pi

[pi](https://pi.dev) is an AI coding agent that runs in the terminal.

Also mounts `~/.pi/agent` for persistent extensions and auth, `~/.agents/skills` for skills, and forwards API keys and pi-related env vars from the host.

### Installation

```bash
ln -sf "$(pwd)/pi/pi" "/usr/local/bin/pi"
pi --build
```

---

## Usage

```bash
# Run in the current directory (uses the base image, unrestricted network)
pi

# Run with a specific language runtime
pi --lang go
pi --lang php8.4
pi --lang php8.5

# Rebuild all images and run
pi --build

# Enable the proxy sidecar (restricted network access via allowlist)
pi --proxy

# Enable the proxy with a custom allowed-domains list
pi --proxy --allowed-domains /path/to/allowed_domains.txt

# Pass flags directly to the agent
pi -- --help
```

---

## How it works

Each agent lives in its own directory with a `Dockerfile` and a bash wrapper script. The wrapper:

1. Builds all image variants on first run, or when `--build` is passed
2. Starts a proxy sidecar container and an isolated internal Docker network
3. Runs the selected agent variant with strict security settings (`--cap-drop=ALL`, `--no-new-privileges`)
4. Bind-mounts the current working directory so the agent can read and edit your files

The Dockerfiles use a multi-stage build based on Microsoft's [`devcontainers/typescript-node`](https://mcr.microsoft.com/en-us/artifact/mar/devcontainers/typescript-node) image:

| Tag      | Contents                                         |
| -------- | ------------------------------------------------ |
| `base`   | Node.js + npm, agent, Git, curl, ca-certificates |
| `go`     | `base` + Go 1.26                                 |
| `php8.4` | `base` + PHP 8.4                                 |
| `php8.5` | `base` + PHP 8.5                                 |

### Security model

Containers run as your host UID (non-root), with all Linux capabilities dropped and `no-new-privileges` enforced. Agents cannot install system packages, access the Docker socket, or escape the container via privilege escalation.

Network access can optionally be restricted by a proxy sidecar (see [Proxy](#proxy) below). When `--proxy` is passed, the agent container is placed on an isolated internal Docker network with no direct internet access — all outbound traffic is forced through the proxy. Without `--proxy`, the container has unrestricted internet access.

---

## Proxy

The proxy is a [tinyproxy](https://tinyproxy.github.io/) sidecar container that enforces an allowlist of permitted hostnames. It runs alongside the agent container and is the agent's only path to the internet.

### How it works

1. **Isolated network** — The wrapper creates a dedicated internal Docker network per run. The agent container joins only this network; it has no direct internet access.
2. **Proxy sidecar** — A `pi-proxy` container starts on both the internal network and the default bridge (so it can reach the internet). The agent's `HTTP_PROXY` / `HTTPS_PROXY` env vars are set to the proxy's address on the internal network.
3. **Allowlist filtering** — At startup, `entrypoint.sh` reads `~/.agents/proxy_allowed_domains.txt` and converts each entry into a tinyproxy regex filter rule:
   - `example.com` → exact match (`^example\.com$`)
   - `*.example.com` → domain + all subdomains (`^(.*\.)?example\.com$`)
   - Lines starting with `#` and blank lines are ignored
4. **Default-deny** — Any hostname not matched by the filter is blocked. Only connections to standard HTTPS/HTTP ports are permitted (tinyproxy `ConnectPort`).
5. **Teardown** — When the agent exits, the wrapper stops the proxy container and removes the network.

### Default allowed domains

The default allowlist is read from `~/.agents/proxy_allowed_domains.txt`. Example:

```
# Allowed domains for the pi agent proxy.
# One entry per line. Wildcards supported: *.example.com
# Lines starting with # are ignored.

# GitHub
github.com
api.github.com
raw.githubusercontent.com
*.githubusercontent.com
*.github.com

# Atlassian
*.atlassian.com
*.atlassian.net

# Services running on host
host.docker.internal
```

To use a different file, pass `--allowed-domains /path/to/file`.

### Bypassing the proxy

The proxy is opt-in — simply omit `--proxy` and the container runs with unrestricted internet access (the default).

```bash
pi  # no proxy, unrestricted network
```

---

## Jira Auth Flow

### Prerequisites (macOS)

Docker Desktop must have **Host Networking** enabled so the OAuth callback from your browser reaches the container:

> Docker Desktop → Settings → Resources → Network → **Enable host networking**

---

### One-time setup: persist credentials

`~/.config/acli` is already mounted into the container, so credentials survive restarts.

---

### Auth workflow (only needed once, or after token expiry)

Run login command inside the docker container:

```bash
acli jira auth login --web
```

The browser opens automatically. Complete the Atlassian OAuth flow — the callback redirects back to the browser and auth finishes without any manual steps.

**Verify:**
```bash
acli jira auth status
```
```
✓ Authenticated
  Site: your-org.atlassian.net
  Email: your@email.com
  Authentication Type: oauth
```
