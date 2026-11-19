"""Exercise wrapper arguments with fake Docker; no daemon or image required."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


WRAPPER = Path(__file__).with_name("pi").resolve()


class AttachmentMountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.capture = self.root / "docker-args.json"
        self.executable("docker", """#!/usr/bin/env python3
import json, os, sys
if sys.argv[1] == "run":
    with open(os.environ["DOCKER_ARGS_FILE"], "w") as output:
        json.dump(sys.argv[2:], output)
""")
        # Avoid leaving the wrapper's browser bridge following a log in tests.
        self.executable("tail", "#!/bin/sh\nexit 0\n")
        self.env = {"HOME": str(self.root / "home"),
                    "PATH": str(self.bin) + os.pathsep + os.environ["PATH"],
                    "DOCKER_ARGS_FILE": str(self.capture)}

    def executable(self, name, content):
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o755)

    def invoke(self, *args):
        result = subprocess.run(["bash", str(WRAPPER), "--", *args],
                                cwd=self.workspace, env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(self.capture.read_text())

    def test_launch_without_attachments(self):
        args = self.invoke()
        self.assertIn("pi-yolo:base", args)

    def test_external_attachment_is_mounted_readonly_at_same_path(self):
        attachment = self.root / "planning input.json"
        attachment.write_text('{"key":"DME-898"}')
        args = self.invoke("@" + str(attachment))
        mount = str(attachment) + ":" + str(attachment) + ":ro"
        self.assertIn(mount, args)
        self.assertEqual(args[args.index(mount) - 1], "--volume")
        self.assertIn("@" + str(attachment), args)
        self.assertNotIn(str(self.root) + ":" + str(self.root) + ":ro", args)

    def test_attachment_in_checkout_keeps_existing_workspace_permissions(self):
        attachment = self.workspace / "source.txt"
        attachment.write_text("context")
        args = self.invoke("@" + str(attachment))
        self.assertNotIn(str(attachment) + ":" + str(attachment) + ":ro", args)

    def test_repeated_attachment_mount_is_deduplicated(self):
        attachment = self.root / "input.json"
        attachment.write_text("{}")
        args = self.invoke("@" + str(attachment), "@" + str(attachment))
        self.assertEqual(args.count(str(attachment) + ":" + str(attachment) + ":ro"), 1)

    def test_missing_attachment_does_not_create_mount(self):
        attachment = self.root / "missing.json"
        args = self.invoke("@" + str(attachment))
        self.assertNotIn(str(attachment) + ":" + str(attachment) + ":ro", args)


if __name__ == "__main__":
    unittest.main()
