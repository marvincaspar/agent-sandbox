# Agent Sandbox

Runs AI coding agents inside isolated Docker containers. Agents get no root access, no Docker socket, and no ability to escalate privileges — safe to run on your host machine.

## How it works

Each agent lives in its own directory with a `Dockerfile` and a bash wrapper script. The wrapper:

1. Builds all image variants on first run, or when `--build` is passed
2. Runs the selected variant with strict security settings (`--cap-drop=ALL`, `--no-new-privileges`)
3. Bind-mounts the current working directory so the agent can read and edit your files

The Dockerfiles use a multi-stage build based on [Chainguard's Node image](https://images.chainguard.dev/directory/image/node/overview):

| Tag      | Contents                                         |
| -------- | ------------------------------------------------ |
| `base`   | Node.js + npm, agent, Git, curl, ca-certificates |
| `go`     | `base` + Go 1.26                                 |
| `php8.4` | `base` + PHP 8.4                                 |
| `php8.5` | `base` + PHP 8.5                                 |

### Security model

Containers run as your host UID (non-root), with all Linux capabilities dropped and `no-new-privileges` enforced. Agents cannot install system packages, access the Docker socket, or escape the container via privilege escalation.

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

# Pass flags directly to the agent
<agent> -- --help
```

---

## Agents

### pi

[pi](https://pi.dev) is an AI coding agent that runs in the terminal.

```bash
ln -sf "$(pwd)/pi/pi" "/usr/local/bin/pi"
pi --build
```

Also mounts `~/.pi/agent` for persistent extensions and auth, `~/.agents/skills` for skills, and forwards API keys and pi-related env vars from the host.

### opencode

[opencode](https://opencode.ai) is an AI coding agent that runs in the terminal.

```bash
ln -sf "$(pwd)/opencode/opencode" "/usr/local/bin/opencode"
opencode --build
```

Also mounts `~/.config/opencode` for persistent configuration across runs.
