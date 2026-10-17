"""Offline adversarial tests. All payloads are inert and assembled in temporary trees."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).absolute().parent.parent


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


installer = load_tool("install_adapter")
auditor = load_tool("audit_release")


class TemporaryTree(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="magi-tools-", dir="/tmp")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "export"
        self.root.mkdir()

    def put(self, relative, text="Safe documentation.\n"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            path.write_bytes(text)
        else:
            path.write_text(text, encoding="utf-8")
        return path


class InstallerTests(TemporaryTree):
    def setUp(self):
        super().setUp()
        self.sources = {
            "hermes": ("skills/magi/SKILL.md", "SKILL.md"),
            "claude-code": ("adapters/claude-code/CLAUDE.md", "CLAUDE.md"),
            "gpt": ("adapters/gpt/INSTRUCTIONS.md", "INSTRUCTIONS.md"),
        }
        for target, (relative, _) in self.sources.items():
            self.put(relative, "# Synthetic " + target + "\nExact bytes: é\n")
        self.put("unrelated.txt", "Never copy this file.\n")
        patcher = mock.patch.object(installer, "SOURCE_ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.destination = self.base / "output"

    def install(self, target="hermes", destination=None, apply=False):
        return installer.install_adapter(
            target, self.destination if destination is None else destination, apply=apply
        )

    def test_dry_run_is_json_and_does_not_write(self):
        before = sorted(str(path.relative_to(self.base)) for path in self.base.rglob("*"))
        with mock.patch.object(installer.os, "mkdir", side_effect=AssertionError("write")):
            plan = self.install()
        self.assertEqual(plan["status"], "planned")
        self.assertEqual(plan["target"], "hermes")
        self.assertEqual([a["action"] for a in plan["actions"]], ["create-directory", "copy-file"])
        self.assertEqual(plan["actions"][1]["source"], self.sources["hermes"][0])
        self.assertEqual(json.loads(json.dumps(plan)), plan)
        self.assertFalse(self.destination.exists())
        self.assertEqual(before, sorted(str(p.relative_to(self.base)) for p in self.base.rglob("*")))

    def test_apply_copies_only_selected_allowlisted_file_and_checks_hash(self):
        import hashlib

        for target, (source, filename) in self.sources.items():
            with self.subTest(target=target):
                destination = self.base / ("output-" + target)
                result = self.install(target, destination, apply=True)
                self.assertEqual(result["status"], "applied")
                self.assertEqual([p.name for p in destination.iterdir()], [filename])
                expected = (self.root / source).read_bytes()
                self.assertEqual((destination / filename).read_bytes(), expected)
                digest = hashlib.sha256(expected).hexdigest()
                self.assertEqual(result["actions"][1]["verified_sha256"], digest)
                self.assertEqual((destination.stat().st_mode & 0o077), 0)
                self.assertEqual(((destination / filename).stat().st_mode & 0o077), 0)

    def test_existing_directory_or_file_is_never_overwritten(self):
        for kind in ("empty", "nonempty", "file"):
            with self.subTest(kind=kind):
                destination = self.base / kind
                if kind == "file":
                    destination.write_text("untouched", encoding="utf-8")
                else:
                    destination.mkdir()
                    if kind == "nonempty":
                        (destination / "keep").write_text("untouched", encoding="utf-8")
                for apply in (False, True):
                    with self.assertRaises(installer.InstallationError):
                        self.install(destination=destination, apply=apply)
                if kind == "file":
                    self.assertEqual(destination.read_text(), "untouched")
                elif kind == "nonempty":
                    self.assertEqual((destination / "keep").read_text(), "untouched")

    def test_destination_and_ancestor_symlinks_are_refused(self):
        real = self.base / "real"
        real.mkdir()
        alias = self.base / "alias"
        alias.symlink_to(real, target_is_directory=True)
        dangling = self.base / "dangling"
        dangling.symlink_to(self.base / "missing")
        for destination in (alias, alias / "output", dangling):
            for apply in (False, True):
                with self.subTest(destination=destination.name, apply=apply):
                    with self.assertRaises(installer.InstallationError):
                        self.install(destination=destination, apply=apply)
        self.assertEqual(list(real.iterdir()), [])

    def test_source_file_symlink_is_refused(self):
        source = self.root / self.sources["hermes"][0]
        source.unlink()
        source.symlink_to(self.root / "unrelated.txt")
        with self.assertRaises(installer.InstallationError):
            self.install(apply=True)
        self.assertFalse(self.destination.exists())

    def test_source_directory_symlink_is_refused(self):
        original = self.root / "skills" / "magi"
        moved = self.root / "moved"
        original.rename(moved)
        original.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(installer.InstallationError):
            self.install()

    def test_source_root_symlink_and_parent_alias_are_refused(self):
        alias = self.base / "source-alias"
        alias.symlink_to(self.root, target_is_directory=True)
        parent_alias = self.base / "parent-alias"
        parent_alias.symlink_to(self.base, target_is_directory=True)
        for source_root in (alias, parent_alias / "export"):
            with mock.patch.object(installer, "SOURCE_ROOT", source_root):
                with self.assertRaises(installer.InstallationError):
                    self.install()

    def test_traversal_source_tree_and_missing_parent_are_refused(self):
        destinations = (
            self.base / "unused" / ".." / "output",
            self.root / "output",
            self.root,
            self.base / "missing-parent" / "output",
        )
        for destination in destinations:
            with self.subTest(destination=str(destination)):
                with self.assertRaises(installer.InstallationError):
                    self.install(destination=destination, apply=True)
        self.assertFalse((self.base / "unused").exists())
        self.assertFalse((self.base / "missing-parent").exists())

    def test_unknown_target_and_nonboolean_apply_are_refused(self):
        for target in ("../hermes", "all", "", "HERmes"):
            with self.assertRaises(installer.InstallationError):
                self.install(target)
        for apply in ("false", 1, None):
            with self.assertRaises(installer.InstallationError):
                self.install(apply=apply)

    def test_binary_oversized_missing_and_special_sources_are_refused(self):
        source = self.root / self.sources["hermes"][0]
        for content in (b"bad\x00bytes", b"\xff", b"a" * (installer.MAX_SOURCE_BYTES + 1)):
            source.write_bytes(content)
            with self.assertRaises(installer.InstallationError):
                self.install(apply=True)
            self.assertFalse(self.destination.exists())
        source.unlink()
        with self.assertRaises(installer.InstallationError):
            self.install()
        if hasattr(os, "mkfifo"):
            os.mkfifo(source)
            with self.assertRaises(installer.InstallationError):
                self.install()

    def test_destination_race_does_not_replace_existing_data(self):
        real_mkdir = installer.os.mkdir

        def raced_mkdir(name, mode=0o777, *, dir_fd=None):
            real_mkdir(name, mode, dir_fd=dir_fd)
            (self.destination / "keep").write_text("untouched", encoding="utf-8")
            raise FileExistsError("synthetic race")

        with mock.patch.object(installer.os, "mkdir", side_effect=raced_mkdir):
            with self.assertRaises(installer.InstallationError):
                self.install(apply=True)
        self.assertEqual((self.destination / "keep").read_text(), "untouched")
        self.assertFalse((self.destination / "SKILL.md").exists())

    def test_readback_failure_is_not_reported_as_success(self):
        original = installer._read_regular_at
        calls = 0

        def corrupt_readback(*args, **kwargs):
            nonlocal calls
            calls += 1
            data, metadata = original(*args, **kwargs)
            return (data + b"corruption", metadata) if calls > 1 else (data, metadata)

        with mock.patch.object(installer, "_read_regular_at", side_effect=corrupt_readback):
            with self.assertRaises(installer.InstallationError):
                self.install(apply=True)
        self.assertFalse(self.destination.exists())

    def test_cli_requires_destination_and_defaults_to_plan(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                installer.main(["hermes"])
        self.assertNotEqual(caught.exception.code, 0)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = installer.main(["gpt", "--destination", str(self.destination)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "planned")
        self.assertFalse(self.destination.exists())


class AuditTests(TemporaryTree):
    def rules(self, findings):
        for finding in findings:
            self.assertEqual(set(finding), {"file", "line", "rule"})
            self.assertFalse(Path(finding["file"]).is_absolute())
            self.assertIs(type(finding["line"]), int)
        return {f["rule"] for f in findings}

    def test_clean_text_and_reserved_examples_pass(self):
        self.put("README.md", "Contact: demo@example.invalid or demo@example.com\n"
                 "Documentation addresses: 192.0.2.1 and 198.51.100.10 and 203.0.113.9\n"
                 "Generic paths: /home/<USER>/project /Users/USERNAME/project\n"
                 "Generic data: /mnt/data/<EXPORT>/file\n")
        self.put(".github/workflows/check.yml", "name: offline-check\n")
        self.put(".gitignore", "__pycache__/\n")
        self.assertEqual(auditor.audit_release(self.root), [])

    def test_realistic_shapes_are_detected_without_disclosing_values(self):
        specimens = [
            ("api-token", "sk" + "-" + "synthetic" * 5),
            ("api-token", "gh" + "p_" + "x" * 36),
            ("api-token", "AK" + "IA" + "Z" * 16),
            ("api-token", "xox" + "b-" + "1" * 12 + "-" + "q" * 24),
            ("api-token", "AIza" + "q" * 35),
            ("api-token", "github" + "_pat_" + "q" * 40),
            ("api-token", "eyJ" + "a" * 12 + "." + "b" * 12 + "." + "c" * 12),
            ("private-key", "-" * 5 + "BEGIN " + "OPENSSH " + "PRIVATE KEY" + "-" * 5),
            ("ssh-key", "ssh" + "-ed25519 " + "A" * 48),
            ("email", "someone" + "@" + "nonexample.invalid"),
            ("absolute-path", "/" + "home" + "/" + "synthetic-person/private"),
            ("absolute-path", "/" + "Users" + "/" + "synthetic-person/private"),
            ("absolute-path", "/" + "mnt/data" + "/" + "synthetic-project/private"),
            ("ip-address", ".".join(("10", "21", "32", "43"))),
            ("ip-address", ".".join(("8", "8", "4", "4"))),
            ("numeric-identifier", "chat" + "_id: -" + "123" * 3),
            ("numeric-identifier", "user" + "_id = " + "321" * 2),
            # Deliberately invalid all-zero phone shape, never a real contact.
            ("numeric-identifier", "+" + "0" * 12),
            ("credential-assignment", "api" + "_key = " + "z" * 20),
        ]
        for number, (rule, payload) in enumerate(specimens):
            with self.subTest(rule=rule, number=number):
                self.put("sample.txt", "Safe line.\n" + payload + "\n")
                findings = auditor.audit_release(self.root)
                self.assertIn(rule, self.rules(findings))
                self.assertTrue(any(f["line"] == 2 for f in findings))
                report = json.dumps(findings)
                self.assertNotIn(payload, report)
                self.assertNotIn(str(self.root), report)

    def test_external_deny_terms_are_case_insensitive_substrings(self):
        deny = self.base / "deny.json"
        deny.write_text(json.dumps(["sYnThEtIc-DeNy-MaRkEr"]), encoding="utf-8")
        self.put("README.md", "prefix-SYNTHETIC-DENY-MARKER-suffix\n")
        findings = auditor.audit_release(self.root, deny_file=deny)
        self.assertIn("deny-term", self.rules(findings))
        self.assertEqual(findings[0]["line"], 1)
        self.assertNotIn("marker", json.dumps(findings).casefold())

    def test_deny_matches_relative_names_too(self):
        deny = self.base / "deny.json"
        deny.write_text(json.dumps(["synthetic-denied"]), encoding="utf-8")
        self.put("prefix-SYNTHETIC-DENIED-suffix.txt")
        findings = auditor.audit_release(self.root, deny_file=deny)
        self.assertIn("deny-term", self.rules(findings))
        self.assertTrue(any(f["line"] == 0 for f in findings))

    def test_invalid_deny_files_fail_closed_and_do_not_echo_their_content(self):
        deny = self.base / "deny.json"
        for content in ("{}", "[42]", '[""]', "not JSON", '["line\\nterm"]', '[true]', '"private-value"'):
            deny.write_text(content, encoding="utf-8")
            findings = auditor.audit_release(self.root, deny_file=deny)
            self.assertIn("deny-file-error", self.rules(findings))
            self.assertNotIn("private-value", json.dumps(findings))
        deny.unlink()
        self.assertIn("deny-file-error", self.rules(auditor.audit_release(self.root, deny_file=deny)))
        inside = self.put("deny.json", "[]")
        self.assertIn("deny-file-error", self.rules(auditor.audit_release(self.root, deny_file=inside)))
        alias = self.base / "alias.json"
        alias.symlink_to(inside)
        self.assertIn("deny-file-error", self.rules(auditor.audit_release(self.root, deny_file=alias)))

    def test_unsafe_names_are_reported_without_reading_runtime_data(self):
        names = (
            ".env", ".env.example", "auth.json", "credentials.json", "state.db",
            "data.sqlite3", "state.sqlite-wal", "snapshot.bak", "key.pem", "key.key",
            "id_ed25519", "activity.log", "events.jsonl", "cookies.txt", "dump.sql",
            "archive.tar.gz", "backup.json", "sessions.json", "MEMORY.md",
        )
        for name in names:
            self.put(name)
        for directory in ("sessions", "backups", "logs", "memories", ".private"):
            self.put(directory + "/do-not-read.txt")
        with mock.patch.object(auditor, "_read_regular_at", side_effect=AssertionError("runtime read")):
            findings = auditor.audit_release(self.root)
        self.assertIn("unsafe-data-file", self.rules(findings))
        self.assertIn("unsafe-directory", self.rules(findings))
        self.assertIn("hidden-directory", self.rules(findings))
        for name in names:
            self.assertTrue(any(f["file"] == name for f in findings), name)

    def test_symlink_files_directories_and_git_are_detected_without_following(self):
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "payload.txt").write_text("never read", encoding="utf-8")
        for name, target in (("file-link", outside / "payload.txt"), ("directory-link", outside), (".git", outside)):
            (self.root / name).symlink_to(target)
        findings = auditor.audit_release(self.root)
        self.assertEqual(len(findings), 3)
        self.assertEqual(self.rules(findings), {"symlink"})

    def test_only_root_git_metadata_is_ignored(self):
        self.put(".git/objects/payload", b"\x00\xff")
        self.assertEqual(auditor.audit_release(self.root), [])
        self.put("nested/.git/payload", "Not ignored.\n")
        self.assertIn("hidden-directory", self.rules(auditor.audit_release(self.root)))

    def test_hidden_file_and_hidden_dir_are_not_broadly_excluded(self):
        self.put(".unexpected.txt")
        self.put(".unexpected/payload.txt")
        self.assertEqual(self.rules(auditor.audit_release(self.root)), {"hidden-file", "hidden-directory"})

    def test_binary_invalid_utf8_oversized_and_special_files_fail_closed(self):
        self.put("nul.txt", b"text\x00text")
        self.put("encoding.txt", b"\xff")
        self.put("control.txt", b"text\x1btext")
        self.put("large.txt", b"a" * (auditor.MAX_FILE_BYTES + 1))
        if hasattr(os, "mkfifo"):
            os.mkfifo(self.root / "pipe")
        findings = auditor.audit_release(self.root)
        rules = self.rules(findings)
        self.assertIn("binary-or-non-utf8", rules)
        self.assertIn("file-too-large", rules)
        if hasattr(os, "mkfifo"):
            self.assertIn("special-file", rules)

    def test_unreadable_files_fail_closed_without_os_error_details(self):
        self.put("unreadable.txt")
        with mock.patch.object(auditor, "_read_regular_at", side_effect=PermissionError("sensitive detail")):
            findings = auditor.audit_release(self.root)
        self.assertIn("unreadable-file", self.rules(findings))
        self.assertNotIn("sensitive", json.dumps(findings))

    def test_invalid_root_and_symlink_ancestors_fail_closed(self):
        alias = self.base / "root-link"
        alias.symlink_to(self.root, target_is_directory=True)
        ancestor = self.base / "ancestor"
        ancestor.symlink_to(self.base, target_is_directory=True)
        for root in (alias, ancestor / "export", self.base / "missing", self.put("file.txt")):
            findings = auditor.audit_release(root)
            self.assertIn("invalid-root", self.rules(findings))

    def test_traversal_limits_fail_closed(self):
        self.put("one.txt")
        self.put("two.txt")
        with mock.patch.object(auditor, "MAX_ENTRIES", 1):
            self.assertIn("scan-limit", self.rules(auditor.audit_release(self.root)))
        with mock.patch.object(auditor, "MAX_TOTAL_BYTES", 1):
            self.assertIn("scan-limit", self.rules(auditor.audit_release(self.root)))
        self.put("first/second/file.txt")
        with mock.patch.object(auditor, "MAX_DEPTH", 1):
            self.assertIn("scan-limit", self.rules(auditor.audit_release(self.root)))

    def test_cli_is_json_redacted_and_returns_zero_or_one(self):
        self.put("clean.txt")
        command = [sys.executable, "-B", str(ROOT / "tools/audit_release.py"), str(self.root), "--pretty"]
        clean = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)
        self.assertEqual(clean.returncode, 0, clean.stderr)
        self.assertEqual(json.loads(clean.stdout), [])
        payload = "sk" + "-" + "inert" * 8
        self.put("sample.txt", payload)
        failed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)
        self.assertEqual(failed.returncode, 1, failed.stderr)
        self.assertIn("api-token", self.rules(json.loads(failed.stdout)))
        self.assertNotIn(payload, failed.stdout + failed.stderr)
        self.assertEqual(failed.stderr, "")

    def test_tool_source_and_test_source_pass_without_broad_file_exclusions(self):
        for relative in ("tools/install_adapter.py", "tools/audit_release.py", "tests/test_tools.py"):
            self.put(relative, (ROOT / relative).read_bytes())
        self.assertEqual(auditor.audit_release(self.root), [])
        # A dangerous addition to the scanner itself must still be detected.
        payload = "sk" + "-" + "inert" * 8
        with (self.root / "tools/audit_release.py").open("a", encoding="utf-8") as stream:
            stream.write("\n# " + payload + "\n")
        self.assertIn("api-token", self.rules(auditor.audit_release(self.root)))


if __name__ == "__main__":
    unittest.main()
