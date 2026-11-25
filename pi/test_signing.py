"""Check SSH signing mounts/configuration without Docker or real credentials."""

import json
import os
from pathlib import Path
import socket
import subprocess

from test_wrapper import WRAPPER, WrapperTestCase


class SigningTests(WrapperTestCase):
    def setUp(self):
        super().setUp()
        self.home = Path(self.env["HOME"])
        self.public_key = self.home / ".ssh" / "git_signing_key.pub"
        self.public_key.parent.mkdir(parents=True)
        self.public_key.write_text("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA signing-test\n")
        self.config = self.home / ".gitconfig"
        self.config.write_text('''[user]
    name = Signing Test
    email = signer@example.test
    signingkey = ~/.ssh/git_signing_key.pub
[commit]
    gpgsign = true
[gpg]
    format = ssh
''')
        self.agent_path = self.root / "agent.sock"
        self.agent = socket.socket(socket.AF_UNIX)
        self.addCleanup(self.agent.close)
        self.agent.bind(str(self.agent_path))
        self.env["SSH_AUTH_SOCK"] = str(self.agent_path)
        self.executable("uname", "#!/bin/sh\necho Darwin\n")
        self.executable("stat", "#!/bin/sh\necho " + str(self.agent_path.stat().st_gid) + "\n")

    def docker_env(self, args):
        return dict(args[i + 1].split("=", 1) for i, arg in enumerate(args) if arg == "--env" and "=" in args[i + 1])

    def assert_rejected(self, message):
        result = subprocess.run(["bash", str(WRAPPER), "--"], cwd=self.workspace,
                                env=self.env, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)
        self.assertFalse(self.capture.exists(), "invalid signing setup must not launch the agent container")

    def test_macos_forwards_agent_and_public_key_with_signing_configuration(self):
        args = self.invoke()
        self.assertIn("type=bind,source=/run/host-services/ssh-auth.sock,target=/run/ssh-agent", args)
        self.assertEqual(args[args.index("--group-add") + 1], "0")
        self.assertEqual(args[args.index("--user") + 1], str(os.getuid()) + ":" + str(os.getgid()))
        self.assertIn("type=bind,source=" + str(self.public_key) + ",target=/run/git-signing-key.pub,readonly", args)
        env = self.docker_env(args)
        self.assertEqual(env["SSH_AUTH_SOCK"], "/run/ssh-agent")
        self.assertEqual(env["GIT_CONFIG_COUNT"], "5")
        config = {env["GIT_CONFIG_KEY_" + str(i)]: env["GIT_CONFIG_VALUE_" + str(i)] for i in range(5)}
        self.assertEqual(config, {"user.name": "Signing Test", "user.email": "signer@example.test",
                                  "gpg.format": "ssh", "user.signingkey": "/run/git-signing-key.pub",
                                  "commit.gpgsign": "true"})
        self.assertFalse(any("source=" + str(self.public_key.parent) + "," in arg for arg in args))
        self.assertFalse(any(".gitconfig" in arg for arg in args))

    def test_linux_uses_host_agent_socket(self):
        self.executable("uname", "#!/bin/sh\necho Linux\n")
        args = self.invoke()
        self.assertIn("type=bind,source=" + str(self.agent_path) + ",target=/run/ssh-agent", args)
        self.assertEqual(args[args.index("--group-add") + 1], str(self.agent_path.stat().st_gid))
        self.assertNotIn("type=bind,source=/run/host-services/ssh-auth.sock,target=/run/ssh-agent", args)

    def test_missing_public_key_fails_before_launch(self):
        self.public_key.unlink()
        self.assert_rejected("public signing key")

    def test_private_key_cannot_be_mounted_as_public_key(self):
        self.public_key.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nnot-a-real-key\n")
        self.assert_rejected("public signing key")

    def test_missing_agent_fails_before_launch(self):
        del self.env["SSH_AUTH_SOCK"]
        self.assert_rejected("SSH_AUTH_SOCK")

    def test_agent_path_must_be_a_socket(self):
        path = self.root / "not-a-socket"
        path.write_text("")
        self.env["SSH_AUTH_SOCK"] = str(path)
        self.assert_rejected("SSH_AUTH_SOCK")

    def test_other_signing_formats_do_not_silently_become_unsigned(self):
        self.config.write_text(self.config.read_text().replace("format = ssh", "format = openpgp"))
        self.assert_rejected("SSH signing")

    def test_disabled_signing_does_not_forward_credentials(self):
        self.config.write_text(self.config.read_text().replace("gpgsign = true", "gpgsign = false"))
        del self.env["SSH_AUTH_SOCK"]
        self.public_key.unlink()
        args = self.invoke()
        self.assertNotIn("SSH_AUTH_SOCK", self.docker_env(args))
        self.assertNotIn("GIT_CONFIG_COUNT", self.docker_env(args))
        self.assertFalse(any("git-signing-key" in arg or "ssh-agent" in arg for arg in args))

    def test_missing_identity_fails_before_launch(self):
        config = self.config.read_text()
        for field in ["    name = Signing Test\n", "    email = signer@example.test\n"]:
            with self.subTest(field=field.strip()):
                self.config.write_text(config.replace(field, ""))
                self.assert_rejected("user.name and user.email")

    def test_public_key_mount_delimiters_are_rejected(self):
        path = self.public_key.with_name("signing,key.pub")
        path.write_text(self.public_key.read_text())
        self.config.write_text(self.config.read_text().replace("~/.ssh/git_signing_key.pub", str(path)))
        self.assert_rejected("public signing key")

    def test_agent_mount_delimiters_are_rejected(self):
        self.executable("uname", "#!/bin/sh\necho Linux\n")
        path = self.root / "agent,socket"
        agent = socket.socket(socket.AF_UNIX)
        self.addCleanup(agent.close)
        agent.bind(str(path))
        self.env["SSH_AUTH_SOCK"] = str(path)
        self.assert_rejected("mount delimiters")

    def test_unsupported_platform_fails_before_launch(self):
        self.executable("uname", "#!/bin/sh\necho FreeBSD\n")
        self.assert_rejected("macOS Docker Desktop and Linux")

    def test_readonly_planning_does_not_get_signing_authority(self):
        del self.env["SSH_AUTH_SOCK"]
        result = subprocess.run(["bash", str(WRAPPER), "--factory-read-only", "--"], cwd=self.workspace,
                                env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(self.capture.read_text())
        self.assertNotIn("SSH_AUTH_SOCK", self.docker_env(args))
        self.assertNotIn("GIT_CONFIG_COUNT", self.docker_env(args))
        self.assertFalse(any("git-signing-key" in arg or "ssh-agent" in arg for arg in args))
