#!/usr/bin/env python3
"""Build an offline, allowlisted source ZIP with normalized metadata.

This is a packaging check, not proof of absence of personal information.
Run in a directory you control, not concurrently writable by untrusted users.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 1024 * 1024
IGNORED_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "build", "dist", "trial"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".toml", ".yml", ".yaml", ".txt", ".cff"}
SPECIAL_FILES = {".gitignore", ".gitattributes", "LICENSE", "NOTICE"}


def no_symlinks(path: Path) -> None:
    for item in [path, *path.parents]:
        if item.is_symlink():
            raise ValueError("symlink path refused")


def safe_relative(value: object) -> str:
    if not isinstance(value, str) or not value or not re.fullmatch(r"[A-Za-z0-9_./-]+", value):
        raise ValueError("invalid allowlist path")
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or ".." in value or any(p in IGNORED_DIRS for p in path.parts):
        raise ValueError("unsafe allowlist path")
    if path.name not in SPECIAL_FILES and path.suffix not in TEXT_SUFFIXES:
        raise ValueError("unsupported allowlist file type")
    if any(part.startswith(".") and part not in {".github", ".gitignore", ".gitattributes"} for part in path.parts):
        raise ValueError("hidden file refused")
    return value


def read_text_bytes(path: Path) -> bytes:
    no_symlinks(path)
    if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("missing or non-regular source file")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("oversized source file")
    with path.open("rb") as handle:
        data = handle.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES or b"\x00" in data:
        raise ValueError("binary or oversized source file")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("source must be UTF-8 text") from exc
    return data


def collect(source: Path) -> dict[str, bytes]:
    no_symlinks(source)
    if not source.is_dir():
        raise ValueError("source directory missing")
    manifest = json.loads(read_text_bytes(source / "release-files.json"))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "magi.release.v1":
        raise ValueError("invalid release manifest schema")
    names = manifest.get("files")
    if not isinstance(names, list) or not names:
        raise ValueError("empty or invalid release allowlist")
    names = [safe_relative(name) for name in names]
    if len(set(name.casefold() for name in names)) != len(names) or "release-files.json" not in names:
        raise ValueError("duplicate paths or missing manifest entry")
    expected = set(names)
    if any(PurePosixPath(name).parts[0].casefold() == "manifest.json" for name in names):
        raise ValueError("generated integrity manifest path is reserved case-insensitively")
    actual = set()
    generated = None
    def walk_error(_error):
        raise ValueError("unreadable source directory")
    for folder, dirs, files in os.walk(source, followlinks=False, onerror=walk_error):
        base = Path(folder)
        for name in list(dirs):
            item = base / name
            if item.is_symlink():
                raise ValueError("symlink directory refused")
            if name in IGNORED_DIRS or name.endswith(".egg-info"):
                dirs.remove(name)
        for name in files:
            item = base / name
            if item.is_symlink():
                raise ValueError("symlink file refused")
            rel = item.relative_to(source).as_posix()
            if rel == "MANIFEST.json":
                generated = json.loads(read_text_bytes(item))
                if not isinstance(generated, dict):
                    raise ValueError("invalid generated integrity manifest")
                continue
            if rel not in expected:
                raise ValueError("unlisted source file: " + rel)
            actual.add(rel)
    if actual != expected:
        raise ValueError("allowlisted source file missing")
    files = {name: read_text_bytes(source / name) for name in sorted(expected)}
    if generated is not None and generated != integrity_manifest(files):
        raise ValueError("generated integrity manifest does not match source bytes")
    return files


def integrity_manifest(files: dict[str, bytes]) -> dict:
    return {
        "schema_version": "magi.archive.v1",
        "source_status": "source_distribution",
        "source_revision_basis": "per_file_sha256",
        "files": [
            {"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in files.items()
        ],
        "excluded": ["git_history", "host_metadata", "private_state", "caches", "build_outputs"],
        "claim": "Integrity manifest only; not a security or privacy certification.",
    }


def zip_entry(name: str, data: bytes, archive: zipfile.ZipFile) -> None:
    info = zipfile.ZipInfo("magi/" + name, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build_release(source: Path, output: Path, *, run_audit: bool = True) -> dict:
    source = Path(os.path.abspath(source))
    output = Path(os.path.abspath(output))
    no_symlinks(source)
    no_symlinks(output)
    if output == source or source in output.parents:
        raise ValueError("output must be outside source")
    if output.exists() or not output.parent.is_dir() or output.suffix.lower() != ".zip":
        raise ValueError("output must be a new ZIP in an existing directory")
    files = collect(source)
    if run_audit:
        auditor = source / "tools" / "audit_release.py"
        if "tools/audit_release.py" not in files:
            raise ValueError("release auditor missing from allowlist")
        result = subprocess.run(
            [sys.executable, str(auditor), str(source)],
            capture_output=True, text=True, timeout=60, check=False,
        )
        if result.returncode != 0:
            raise ValueError("release privacy audit failed; run the auditor separately")
    # Re-read after the audit to catch ordinary edits; not an adversarial race guarantee.
    if files != collect(source):
        raise ValueError("source changed during audit")
    manifest = integrity_manifest(files)
    created = False
    try:
        with output.open("xb") as raw:
            created = True
            with zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in files.items():
                    zip_entry(name, data, archive)
                zip_entry("MANIFEST.json", (json.dumps(manifest, indent=2) + "\n").encode(), archive)
        with zipfile.ZipFile(output) as archive:
            if archive.testzip() is not None:
                raise ValueError("archive integrity failure")
        return {
            "status": "built",
            "files": len(files),
            "archive_entries": len(files) + 1,
            "bytes": output.stat().st_size,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        }
    except Exception:
        if created:
            output.unlink(missing_ok=True)
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = build_release(ROOT, args.output)
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        # Do not echo potentially sensitive exception payloads from paths/JSON input.
        print(json.dumps({"status": "blocked", "error_type": type(exc).__name__,
                          "message": "Packaging checks failed; inspect source allowlist, paths and audit."}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
