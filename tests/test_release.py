"""Release packaging tests use synthetic, disposable file trees only."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

SPEC = importlib.util.spec_from_file_location(
    "release_builder", Path(__file__).resolve().parents[1] / "tools" / "build_release.py"
)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "source"
        self.root.mkdir()
        (self.root / "README.md").write_text("Synthetic release.\n", encoding="utf-8")
        self.names = ["README.md", "release-files.json"]
        self.manifest()

    def manifest(self, names=None):
        (self.root / "release-files.json").write_text(
            json.dumps({"schema_version": "magi.release.v1", "files": names or self.names}),
            encoding="utf-8",
        )

    def build(self, name="release.zip"):
        return builder.build_release(self.root, self.base / name, run_audit=False)

    def test_archive_hashes_and_normalized_metadata(self):
        result = self.build()
        self.assertEqual(result["files"], 2)
        with zipfile.ZipFile(self.base / "release.zip") as archive:
            self.assertIsNone(archive.testzip())
            manifest = json.loads(archive.read("magi/MANIFEST.json"))
            self.assertEqual(manifest["source_status"], "source_distribution")
            self.assertEqual(len(manifest["files"]), 2)
            for item in manifest["files"]:
                data = archive.read("magi/" + item["path"])
                self.assertEqual(item["sha256"], hashlib.sha256(data).hexdigest())
                self.assertEqual(item["size"], len(data))
            for info in archive.infolist():
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(info.comment, b"")
                self.assertEqual(info.extra, b"")
                self.assertFalse(info.filename.startswith("/"))

    def test_notice_and_citation_text_can_be_packaged(self):
        (self.root / "NOTICE").write_text("Synthetic attribution notice.\n", encoding="utf-8")
        (self.root / "CITATION.cff").write_text("cff-version: 1.2.0\n", encoding="utf-8")
        self.names.extend(["NOTICE", "CITATION.cff"])
        self.manifest()
        self.build()
        with zipfile.ZipFile(self.base / "release.zip") as archive:
            self.assertIn("magi/NOTICE", archive.namelist())
            self.assertIn("magi/CITATION.cff", archive.namelist())

    def test_reproducible_zip(self):
        self.build("a.zip")
        self.build("b.zip")
        self.assertEqual((self.base / "a.zip").read_bytes(), (self.base / "b.zip").read_bytes())

    def test_rebuild_downloaded_source_and_reject_tampering(self):
        self.build()
        with zipfile.ZipFile(self.base / "release.zip") as archive:
            archive.extractall(self.base / "unpacked")
        source = self.base / "unpacked" / "magi"
        output = self.base / "rebuilt.zip"
        builder.build_release(source, output, run_audit=False)
        self.assertEqual(output.read_bytes(), (self.base / "release.zip").read_bytes())
        (source / "MANIFEST.json").write_text('{}')
        with self.assertRaises(ValueError):
            builder.build_release(source, self.base / "tampered.zip", run_audit=False)

    def test_reserved_manifest_not_an_input(self):
        (self.root / "MANIFEST.json").write_text('{}')
        self.manifest(self.names + ["MANIFEST.json"])
        with self.assertRaises(ValueError):
            self.build()

    def test_reserved_manifest_case_and_directory_collisions(self):
        import shutil
        variants = ("manifest.json", "Manifest.json", "MANIFEST.JSON",
                    "manifest.json/child.md", "MANIFEST.JSON/child.md")
        for name in variants:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                source = Path(temp) / "source"
                shutil.copytree(self.root, source)
                target = source / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('{}', encoding="utf-8")
                (source / "release-files.json").write_text(json.dumps({
                    "schema_version": "magi.release.v1", "files": self.names + [name]
                }), encoding="utf-8")
                with self.assertRaises(ValueError):
                    builder.build_release(source, Path(temp) / "output.zip", run_audit=False)

    def test_existing_output_not_overwritten(self):
        out = self.base / "release.zip"
        out.write_bytes(b"keep")
        with self.assertRaises(ValueError):
            self.build()
        self.assertEqual(out.read_bytes(), b"keep")

    def test_unlisted_file_blocks(self):
        (self.root / "notes.txt").write_text("not approved")
        with self.assertRaises(ValueError):
            self.build()
        self.assertFalse((self.base / "release.zip").exists())

    def test_missing_file_blocks(self):
        self.manifest(self.names + ["missing.md"])
        with self.assertRaises(ValueError):
            self.build()

    def test_unsafe_manifest_paths(self):
        for bad in ["../outside.md", "/outside.md", "a\\b.md", "./README.md", ".git/config", "notes..md"]:
            with self.subTest(bad=bad):
                self.manifest(["release-files.json", bad])
                with self.assertRaises(ValueError):
                    self.build()

    def test_duplicates_and_non_strings(self):
        for bad in [["README.md", "README.md"], ["README.md", "readme.md"], [True]]:
            with self.subTest(bad=bad):
                self.manifest(bad)
                with self.assertRaises(ValueError):
                    self.build()

    def test_secret_file_not_allowed_even_in_manifest(self):
        (self.root / ".env").write_text("INERT=fixture")
        self.manifest(self.names + [".env"])
        with self.assertRaises(ValueError):
            self.build()

    def test_binary_and_oversized_input(self):
        for data in [b"binary\x00data", b"x" * (1024 * 1024 + 1)]:
            (self.root / "README.md").write_bytes(data)
            with self.assertRaises(ValueError):
                self.build()

    def test_git_history_excluded(self):
        (self.root / ".git").mkdir()
        (self.root / ".git" / "config").write_text("synthetic metadata")
        self.build()
        with zipfile.ZipFile(self.base / "release.zip") as archive:
            self.assertFalse(any(".git/" in name for name in archive.namelist()))

    def test_output_must_be_outside_source(self):
        with self.assertRaises(ValueError):
            builder.build_release(self.root, self.root / "out.zip", run_audit=False)

    def test_symlink_source_and_output_parent(self):
        try:
            (self.root / "link.md").symlink_to(self.root / "README.md")
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable")
        with self.assertRaises(ValueError):
            self.build()
        (self.root / "link.md").unlink()
        alias = self.base / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            builder.build_release(alias, self.base / "out.zip", run_audit=False)
        parent = self.base / "destination"
        parent.symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(ValueError):
            builder.build_release(self.root, parent / "out.zip", run_audit=False)


if __name__ == "__main__":
    unittest.main()
