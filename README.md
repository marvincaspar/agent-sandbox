# Agent Sandbox

Runs AI coding agents inside isolated Docker containers. Agents get no root access, no Docker socket, and no ability to escalate privileges — safe to run on your host machine.

---

## Agents

### pi

[pi](https://pi.dev) is an AI coding agent that runs in the terminal.

Mounts `~/.pi/agent` for persistent extensions and auth, `~/.agents/skills` for skills, and forwards API keys and pi-related env vars from the host.

#### Installation

```bash
ln -sf "$(pwd)/pi/pi" "/usr/local/bin/pi"
pi --build
```

#### Usage

```bash
# Run in the current directory (uses the base image, unrestricted network)
pi

# Run with a specific language runtime
pi --lang go
pi --lang php8.5

# Rebuild all images and run
pi --build

# Enable the proxy sidecar (restricted network access via allowlist)
pi --proxy

# Enable the proxy with a custom allowed-domains list
pi --proxy --allowed-domains /path/to/allowed_domains.txt

# Pass flags directly to the agent
pi -- --help

# Attach a host file outside the working checkout (mounted read-only)
pi @/absolute/path/to/planning-input.json
```

Explicit absolute `@file` arguments outside the working checkout are bind-mounted
read-only at the same path inside the container. Only the named files are exposed,
not their parent directories. Files already under the checkout keep the existing
workspace mount permissions. Relative attachments continue to resolve from the
working directory. Host file permissions still apply; the container runs as your
host UID. Temporary files remain the caller's responsibility to remove.

Explicit absolute `--extension /path/to/extension.ts` (or `-e`) files outside the
checkout are also mounted read-only. For the factory's export extension,
`--factory-plan-output /path/to/proposal.json` mounts only that existing regular
file read-write at the same path. Symlink/missing output files and conflicting
read/write mounts are rejected. The flag is still forwarded to Pi, where the trusted
extension consumes it. No parent directory or authoritative plan store is exposed.
The factory pre-creates and later removes this private transport file. This flag
is intended for trusted callers, not model-selected paths.

Factory planning sessions use `--factory-read-only` before the `--` separator.
In this mode, the container working directory is an empty read-only tmpfs at
`/factory-workspace`, not a bind mount of the host working directory. Repeated
`--factory-repository /absolute/path` options expose repository directories
read-only. Context, extension, and handoff files remain explicit file mounts,
including files under the host working directory. Normal sessions keep their
existing writable checkout bind mount.

These are wrapper-only changes; no image rebuild is needed. Ensure the `pi` command
points to this updated wrapper. Test the mount arguments without Docker using:

```sh
python3 -m unittest discover -s pi -p 'test_*.py'
```

To use MySQL running on the host, rebuild the image with `pi --build`, then connect over TCP from inside Pi's container:

```bash
mysql --host=host.docker.internal --port=3306 --user=YOUR_USER --password
```

Enter the password at the prompt; don't put it on the command line. The host MySQL server must accept TCP connections from Docker, and the user must have permission to connect from the container. `localhost` inside Pi refers to the container, not the host.

---

### opencode

[opencode](https://opencode.ai) is an open source AI coding agent that runs in the terminal.

Mounts `~/.config/opencode` for persistent config and sessions, `~/.agents/skills` for skills, and forwards API keys and opencode-related env vars from the host.

#### Installation

```bash
ln -sf "$(pwd)/opencode/opencode" "/usr/local/bin/opencode"
opencode --build
```

#### Usage

```bash
# Run in the current directory (uses the base image, unrestricted network)
opencode

# Run with a specific language runtime
opencode --lang go
opencode --lang php8.5

# Rebuild all images and run
opencode --build

# Enable the proxy sidecar (restricted network access via allowlist)
opencode --proxy

# Enable the proxy with a custom allowed-domains list
opencode --proxy --allowed-domains /path/to/allowed_domains.txt

# Pass flags directly to the agent
opencode -- --help
```

---

## How it works

Each agent lives in its own directory with a `Dockerfile` and a bash wrapper script. The wrapper:

1. Builds all image variants on first run, or when `--build` is passed
2. Starts a proxy sidecar container and an isolated internal Docker network
3. Runs the selected agent variant with strict security settings (`--cap-drop=ALL`, `--no-new-privileges`)
4. Bind-mounts the current working directory so the agent can read and edit your files

The Dockerfiles use a multi-stage build based on Chainguard's [`node:latest-dev`](https://images.chainguard.dev/directory/image/node/overview) image:

| Tag      | Contents                                                |
| -------- | ------------------------------------------------------- |
| `base`   | Node.js + npm, agent binary, Git, curl, ca-certificates |
| `go`     | `base` + Go 1.26                                        |
| `php8.5` | `base` + PHP 8.5                                        |

### Security model

Containers run as your host UID (non-root), with all Linux capabilities dropped and `no-new-privileges` enforced. Agents cannot install system packages, access the Docker socket, or escape the container via privilege escalation.

Network access can optionally be restricted by a proxy sidecar (see [Proxy](#proxy) below). When `--proxy` is passed, the agent container is placed on an isolated internal Docker network with no direct internet access — all outbound traffic is forced through the proxy. Without `--proxy`, the container has unrestricted internet access.

---

## Proxy

The proxy is a [tinyproxy](https://tinyproxy.github.io/) sidecar container that enforces an allowlist of permitted hostnames. It runs alongside the agent container and is the agent's only path to the internet.

### How it works

1. **Isolated network** — The wrapper creates a dedicated internal Docker network per run. The agent container joins only this network; it has no direct internet access.
2. **Proxy sidecar** — A `pi-proxy` / `opencode-proxy` container starts on both the internal network and the default bridge (so it can reach the internet). The agent's `HTTP_PROXY` / `HTTPS_PROXY` env vars are set to the proxy's address on the internal network.
3. **Allowlist filtering** — At startup, `entrypoint.sh` reads `~/.agents/proxy_allowed_domains.txt` and converts each entry into a tinyproxy regex filter rule:
   - `example.com` → exact match (`^example\.com$`)
   - `*.example.com` → domain + all subdomains (`^(.*\.)?example\.com$`)
   - Lines starting with `#` and blank lines are ignored
4. **Default-deny** — Any hostname not matched by the filter is blocked. Only connections to standard HTTPS/HTTP ports are permitted (tinyproxy `ConnectPort`).
5. **Teardown** — When the agent exits, the wrapper stops the proxy container and removes the network.

### Default allowed domains

The default allowlist is read from `~/.agents/proxy_allowed_domains.txt`. Example:

```
# Allowed domains for the agent proxy.
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
pi        # no proxy, unrestricted network
opencode  # no proxy, unrestricted network
```

---

## Jira MCP authentication

Keep the Jira server in `~/.pi/agent/mcp.json` alongside any existing MCP servers:

```json
{
  "settings": { "oauthCredentialStore": "encrypted-file" },
  "mcpServers": {
    "jira": { "url": "https://mcp.atlassian.com/v1/mcp", "auth": "oauth" }
  }
}
```

On the **host**, create the encryption key file once (do not overwrite an existing key):

```bash
mkdir -p "$HOME/.config"
if [ ! -e "$HOME/.config/pi-mcp-oauth.key" ]; then
  (umask 077; openssl rand -base64 32 > "$HOME/.config/pi-mcp-oauth.key")
fi
```

Run `pi` normally. If the file exists, the wrapper reads it and forwards `PI_MCP_ADAPTER_OAUTH_FILE_KEY` into the container automatically; no shell export is needed. Keep the key file private and backed up—replacing it makes saved OAuth credentials unreadable. Run `/mcp-auth jira` in Pi, approve access in the host browser, and paste the **full failed localhost redirect URL** into Pi's callback prompt. Do not paste it into chat: it contains a short-lived authorization code. No Docker host networking or API token is needed. Check the server in `/mcp`.
