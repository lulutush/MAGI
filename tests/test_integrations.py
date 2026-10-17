"""Exercise documented CLIs and adapters, without any live agent or API."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def invoke(*args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True,
                          text=True, timeout=20, env=env, check=False)


class IntegrationTests(unittest.TestCase):
    def test_version_and_route_cli(self):
        version = invoke("-m", "magi", "--version")
        self.assertEqual(version.returncode, 0, version.stderr)
        self.assertIn("0.1.0", version.stdout)
        for task in ["Check the current server status", "Vérifie l'état actuel du serveur"]:
            routed = invoke("-m", "magi", "route", task, "--pretty")
            self.assertEqual(routed.returncode, 0, routed.stderr)
            self.assertIsInstance(json.loads(routed.stdout), dict)

    def test_missing_evidence_and_artifact_cli(self):
        missing = invoke("-m", "magi", "gate", "Check the current server status", "--pretty")
        self.assertEqual(missing.returncode, 2, missing.stdout + missing.stderr)
        self.assertIn(json.loads(missing.stdout)["status"], ["unverified", "partial"])
        valid = invoke("-m", "magi", "validate", "examples/artifact.json", "--pretty")
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
        self.assertIsInstance(json.loads(valid.stdout), dict)

    def test_adapter_install_and_readback(self):
        mapping = {
            "hermes": ("skills/magi/SKILL.md", "SKILL.md"),
            "claude-code": ("adapters/claude-code/CLAUDE.md", "CLAUDE.md"),
            "gpt": ("adapters/gpt/INSTRUCTIONS.md", "INSTRUCTIONS.md"),
        }
        with tempfile.TemporaryDirectory() as temp:
            for target, (source, name) in mapping.items():
                destination = Path(temp) / target
                args = ("tools/install_adapter.py", target, "--destination", str(destination))
                preview = invoke(*args)
                self.assertEqual(preview.returncode, 0, preview.stdout + preview.stderr)
                self.assertFalse(destination.exists())
                applied = invoke(*args, "--apply")
                self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
                self.assertEqual(sorted(p.name for p in destination.iterdir()), [name])
                self.assertEqual((destination / name).read_bytes(), (ROOT / source).read_bytes())
                again = invoke(*args, "--apply")
                self.assertNotEqual(again.returncode, 0)
                self.assertEqual(hashlib.sha256((destination / name).read_bytes()).digest(),
                                 hashlib.sha256((ROOT / source).read_bytes()).digest())

    def test_documented_adapter_size_and_skill_metadata(self):
        skill = (ROOT / "skills/magi/SKILL.md").read_text()
        self.assertTrue(skill.startswith("---\n"))
        self.assertRegex(skill, r"(?m)^name: ['\"]?magi['\"]?$")
        self.assertRegex(skill, r"(?m)^description:")
        self.assertLess(len(skill), 8000)
        self.assertLess(len((ROOT / "adapters/gpt/INSTRUCTIONS.md").read_text()), 8000)
        self.assertLessEqual(len((ROOT / "adapters/claude-code/CLAUDE.md").read_text().splitlines()), 150)

    def test_local_markdown_links_resolve(self):
        failures = []
        for path in ROOT.rglob("*.md"):
            if any(part in {".git", ".venv", "build", "dist", "trial"} for part in path.relative_to(ROOT).parts):
                continue
            for link in re.findall(r"\]\(([^)\s]+)(?:\s+[^)]*)?\)", path.read_text()):
                if link.startswith(("http:", "https:", "#", "mailto:")):
                    continue
                dest = link.split("#", 1)[0]
                if dest and not (path.parent / dest).exists():
                    failures.append(path.relative_to(ROOT).as_posix() + ": " + link)
        self.assertEqual(failures, [])

    def test_python_310_syntax_and_no_runtime_network_import(self):
        for path in (ROOT / "magi").glob("*.py"):
            tree = ast.parse(path.read_text(), feature_version=(3, 10))
            names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names.update(x.name.split(".")[0] for x in node.names)
                elif isinstance(node, ast.ImportFrom):
                    names.add((node.module or "").split(".")[0])
            self.assertFalse(names & {"requests", "httpx", "urllib", "http", "socket", "subprocess"})


if __name__ == "__main__":
    unittest.main()
