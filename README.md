# Agent Sandbox

Runs AI coding agents inside isolated Docker containers. Agents get no root access, no Docker socket, and no ability to escalate privileges — safe to run on your host machine.

## How it works

Each agent lives in its own directory with a `Dockerfile` and a bash wrapper script. The wrapper:

1. Builds all image variants on first run, or when `--build` is passed
2. Starts a proxy sidecar container and an isolated internal Docker network
3. Runs the selected agent variant with strict security settings (`--cap-drop=ALL`, `--no-new-privileges`)
4. Bind-mounts the current working directory so the agent can read and edit your files

The Dockerfiles use a multi-stage build based on [Chainguard's Node image](https://images.chainguard.dev/directory/image/node/overview):

| Tag      | Contents                                         |
| -------- | ------------------------------------------------ |
| `base`   | Node.js + npm, agent, Git, curl, ca-certificates |
| `go`     | `base` + Go 1.26                                 |
| `php8.4` | `base` + PHP 8.4                                 |
| `php8.5` | `base` + PHP 8.5                                 |

### Security model

Containers run as your host UID (non-root), with all Linux capabilities dropped and `no-new-privileges` enforced. Agents cannot install system packages, access the Docker socket, or escape the container via privilege escalation.

Network access is restricted by a proxy sidecar (see [Proxy](#proxy) below). The agent container is placed on an isolated internal Docker network with no direct internet access — all outbound traffic is forced through the proxy.

### Usage

```bash
# Run in the current directory (uses the base image)
<agent>

# Run with a specific language runtime
<agent> --lang go
<agent> --lang php8.4
<agent> --lang php8.5

# Rebuild all images and run
<agent> --build

# Run without network restrictions (unrestricted internet access)
<agent> --no-proxy

# Use a custom allowed-domains list
<agent> --allowed-domains /path/to/allowed_domains.txt

# Pass flags directly to the agent
<agent> -- --help
```

---

## Proxy

The proxy is a [tinyproxy](https://tinyproxy.github.io/) sidecar container that enforces an allowlist of permitted hostnames. It runs alongside the agent container and is the agent's only path to the internet.

### How it works

1. **Isolated network** — The wrapper creates a dedicated internal Docker network per run. The agent container joins only this network; it has no direct internet access.
2. **Proxy sidecar** — A `pi-proxy` container starts on both the internal network and the default bridge (so it can reach the internet). The agent's `HTTP_PROXY` / `HTTPS_PROXY` env vars are set to the proxy's address on the internal network.
3. **Allowlist filtering** — At startup, `entrypoint.sh` reads `allowed_domains.txt` and converts each entry into a tinyproxy regex filter rule:
   - `example.com` → exact match (`^example\.com$`)
   - `*.example.com` → domain + all subdomains (`^(.*\.)?example\.com$`)
   - Lines starting with `#` and blank lines are ignored
4. **Default-deny** — Any hostname not matched by the filter is blocked. Only connections to standard HTTPS/HTTP ports are permitted (tinyproxy `ConnectPort`).
5. **Teardown** — When the agent exits, the wrapper stops the proxy container and removes the network.

### Default allowed domains

Defined in `proxy/allowed_domains.txt`:

| Category            | Domains                                                                                                |
| ------------------- | ------------------------------------------------------------------------------------------------------ |
| GitHub              | `github.com`, `api.github.com`, `raw.githubusercontent.com`, `*.github.com`, `*.githubusercontent.com` |
| Local / development | `host.docker.internal`                                                                                 |

To extend the list, add entries to `proxy/allowed_domains.txt` or pass a custom file with `--allowed-domains`.

### Bypassing the proxy

Pass `--no-proxy` to skip the sidecar entirely. The agent container will have unrestricted internet access.

```bash
pi --no-proxy
```

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

## Jira Auth Flow

### Why OAuth doesn't work automatically in Docker

`acli jira auth login --web` starts a temporary local HTTP server inside the container to receive the OAuth callback (e.g. `http://127.0.0.1:53197/callback`). After you authorize in the browser, Atlassian redirects your browser to that URL.

The problem: **your browser runs on the Mac host, not inside the container.** So `127.0.0.1:53197` in the browser refers to the Mac's loopback — not the container's. The callback never reaches the acli server and you get "This site can't be reached."

Two approaches that don't fix this:
- **`--network=host`** — on macOS, Docker Desktop runs inside a Linux VM. Host networking attaches to the VM's network, not the Mac's, so `127.0.0.1` still doesn't bridge correctly.
- **Port mapping (`-p 53197:53197`)** — acli picks a random port on every run, so you can't pre-configure the right port in `docker run`.

The workaround is to manually complete the callback from inside the container using `curl`.

---

### One-time setup: persist credentials

Mount the acli config directory so you don't need to re-authenticate after every container restart:

```
~/.config/acli:/home/piuser/.config/acli
```

Credentials are stored in `/home/piuser/.config/acli/jira_config.yaml` (OAuth token) and related files in that directory.

---

### Auth workflow (only needed once, or after token expiry)

You need **two terminals** exec'd into the container.

**Terminal 1** — start the OAuth flow:
```bash
acli jira auth login --web
```

The process starts a local callback server and writes the OAuth URL to `/tmp/oauth-url.txt`, then waits.

**Terminal 2** — get the URL:
```bash
cat /tmp/oauth-url.txt
```

Open the printed URL in your **host browser** and complete the Atlassian OAuth flow. When it finishes, the browser will try to redirect to `http://127.0.0.1:<port>/callback?code=...&state=...` and show "This site can't be reached." **This is expected.** Copy the full URL from the browser address bar.

**Terminal 2** — forward the callback manually into the container:
```bash
curl "http://127.0.0.1:<port>/callback?code=<CODE>&state=<STATE>"
```

Paste the full URL from the browser address bar (replace everything after `curl `).

**Terminal 1** — select your site:
```
> https://your-org.atlassian.net
```

Pick the site and the auth process completes normally.

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
