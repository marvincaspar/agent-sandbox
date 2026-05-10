# Agent Sandbox

Runs AI coding agents inside isolated Docker containers. Agents get no root access, no Docker socket, and no ability to escalate privileges — safe to run on your host machine.

## pi

[pi](https://pi.dev) is an AI coding agent that runs in the terminal.

### How it works

```
pi/
├── Dockerfile   # Multi-stage image with Node, pi agent, and optional language runtimes
└── pi           # Bash wrapper that launches the container
```

The `pi` wrapper script:

1. Builds all image variants (`pi-yolo:base`, `pi-yolo:go`, `pi-yolo:php8.4`, `pi-yolo:php8.5`) on first run, or when `--build` is passed
2. Runs the selected variant with strict security settings (`--cap-drop=ALL`, `--no-new-privileges`)
3. Bind-mounts the current working directory so the agent can read and edit your files
4. Mounts `~/.pi/agent` for persistent extensions and auth across runs
5. Mounts `~/.agents/skills` so skills are available inside the container
6. Forwards API keys and pi-related env vars from the host into the container

The Dockerfile uses a multi-stage build based on [Chainguard's Node image](https://images.chainguard.dev/directory/image/node/overview):

| Tag      | Contents                                            |
| -------- | --------------------------------------------------- |
| `base`   | Node.js + npm, pi agent, Git, curl, ca-certificates |
| `go`     | `base` + Go 1.26                                    |
| `php8.4` | `base` + PHP 8.4                                    |
| `php8.5` | `base` + PHP 8.5                                    |

### Installation

Run the following command to symlink `pi` into `/usr/local/bin`:

```bash
ln -sf "$(pwd)/pi/pi" "/usr/local/bin/pi"
```

Then build the Docker images:

```bash
pi --build
```

### Usage

```bash
# Run pi in the current directory (uses the base image)
pi

# Run pi with a specific language runtime
pi --lang go
pi --lang php8.4
pi --lang php8.5

# Rebuild all images and run
pi --build

# Pass flags directly to the pi agent
pi -- --help
```

### Security model

The container runs as your host UID (non-root), with all Linux capabilities dropped and `no-new-privileges` enforced. The agent cannot install system packages, access the Docker socket, or escape the container via privilege escalation.
