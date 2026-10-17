#!/usr/bin/env python3
"""Prepare one adapter; copy it only with explicit --apply approval.

No profile discovery, configuration reads, environment inspection, network access,
recursive copying, or shell execution. The destination's parent must already
exist. Source and destination paths must contain no symlink components. This
implementation deliberately fails closed without POSIX no-follow/dir-fd support.
"""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat


SOURCE_ROOT = Path(__file__).absolute().parent.parent
SOURCES = {
    "hermes": ("skills/magi/SKILL.md", "SKILL.md"),
    "claude-code": ("adapters/claude-code/CLAUDE.md", "CLAUDE.md"),
    "gpt": ("adapters/gpt/INSTRUCTIONS.md", "INSTRUCTIONS.md"),
}
MAX_SOURCE_BYTES = 1_048_576


class InstallationError(Exception):
    """A safe, value-free error code, not an underlying OS error message."""


def _absolute_path(value):
    raw = os.fspath(value)
    if not isinstance(raw, str) or not raw or any(ord(char) < 32 for char in raw):
        raise InstallationError("invalid-path")
    path = Path(raw)
    if ".." in path.parts:
        raise InstallationError("path-traversal")
    # abspath does not resolve links; opening each component below rejects them.
    return Path(os.path.abspath(path))


def _check_platform():
    if not all(hasattr(os, name) for name in ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK")):
        raise InstallationError("safe-filesystem-operations-unavailable")
    if os.open not in os.supports_dir_fd or os.stat not in os.supports_dir_fd:
        raise InstallationError("safe-filesystem-operations-unavailable")


def _directory_flags():
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)


@contextmanager
def _open_directory(path):
    descriptor = os.open(path.anchor, _directory_flags())
    try:
        for component in path.parts[1:]:
            child = os.open(component, _directory_flags(), dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


def _identity(metadata):
    return metadata.st_dev, metadata.st_ino


def _snapshot(metadata):
    return (_identity(metadata), metadata.st_size, metadata.st_mtime_ns,
            metadata.st_ctime_ns, metadata.st_mode, metadata.st_nlink)


def _read_regular_at(directory, name, limit=MAX_SOURCE_BYTES):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(name, flags, dir_fd=directory)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise InstallationError("unsafe-file-type")
        if before.st_size > limit:
            raise InstallationError("source-too-large")
        chunks = []
        length = 0
        while length <= limit:
            chunk = os.read(descriptor, min(65_536, limit + 1 - length))
            if not chunk:
                break
            chunks.append(chunk)
            length += len(chunk)
        after = os.fstat(descriptor)
        current = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if _snapshot(before) != _snapshot(after) or _snapshot(after) != _snapshot(current):
            raise InstallationError("file-changed-during-read")
        if length > limit or length != before.st_size:
            raise InstallationError("source-too-large-or-changed")
        return b"".join(chunks), after
    finally:
        os.close(descriptor)


def _read_source(root, relative):
    source = root / relative
    with _open_directory(source.parent) as directory:
        data, _ = _read_regular_at(directory, source.name)
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        raise InstallationError("source-not-utf8-text") from None
    if any(ord(char) < 32 and char not in "\t\n\r" for char in text):
        raise InstallationError("source-not-utf8-text")
    return data


def _require_absent(directory, name):
    try:
        os.stat(name, dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise InstallationError("destination-already-exists")


def _check_binding(path, descriptor):
    with _open_directory(path) as current:
        if _identity(os.fstat(current)) != _identity(os.fstat(descriptor)):
            raise InstallationError("directory-changed")


def _rollback(parent, name, directory, directory_metadata, file_name, file_metadata):
    """Remove only objects we created and still own; never remove replacements."""
    if directory is not None and file_metadata is not None:
        try:
            current = os.stat(file_name, dir_fd=directory, follow_symlinks=False)
            if _identity(current) == _identity(file_metadata):
                os.unlink(file_name, dir_fd=directory)
        except OSError:
            pass
    if directory_metadata is not None:
        try:
            current = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if _identity(current) == _identity(directory_metadata):
                # rmdir refuses a nonempty directory; this is never recursive.
                os.rmdir(name, dir_fd=parent)
        except OSError:
            pass


def _apply(parent, destination, file_name, data, digest):
    directory = None
    directory_metadata = None
    file_metadata = None
    try:
        _check_binding(destination.parent, parent)
        os.mkdir(destination.name, mode=0o700, dir_fd=parent)
        directory_metadata = os.stat(destination.name, dir_fd=parent, follow_symlinks=False)
        directory = os.open(destination.name, _directory_flags(), dir_fd=parent)
        if _identity(directory_metadata) != _identity(os.fstat(directory)):
            raise InstallationError("directory-changed")
        _check_binding(destination, directory)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_NONBLOCK
        descriptor = os.open(file_name, flags, mode=0o600, dir_fd=directory)
        try:
            file_metadata = os.fstat(descriptor)
            if not stat.S_ISREG(file_metadata.st_mode) or file_metadata.st_nlink != 1:
                raise InstallationError("unsafe-output-type")
            remaining = memoryview(data)
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    raise InstallationError("incomplete-write")
                remaining = remaining[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        readback, readback_metadata = _read_regular_at(directory, file_name)
        if (_identity(readback_metadata) != _identity(file_metadata)
                or hashlib.sha256(readback).hexdigest() != digest):
            raise InstallationError("readback-verification-failed")
        if os.listdir(directory) != [file_name]:
            raise InstallationError("unexpected-output-files")
        _check_binding(destination, directory)
        os.fsync(directory)
        os.fsync(parent)
    except (OSError, InstallationError):
        _rollback(parent, destination.name, directory, directory_metadata, file_name, file_metadata)
        raise
    finally:
        if directory is not None:
            os.close(directory)


def install_adapter(target, destination, *, apply=False):
    """Return a JSON-ready plan/result. SOURCE_ROOT is patchable in offline tests.

    Dry-run opens only the selected source and existing directory descriptors;
    it creates nothing. --apply always validates a fresh plan for this one target.
    An interrupted write may leave a private partial directory: inspect it instead
    of reusing it. Existing destinations, even empty ones, are always rejected.
    """
    if target not in SOURCES:
        raise InstallationError("unsupported-target")
    if type(apply) is not bool:
        raise InstallationError("apply-must-be-boolean")
    try:
        _check_platform()
        root = _absolute_path(SOURCE_ROOT)
        destination = _absolute_path(destination)
        if destination == root or root in destination.parents:
            raise InstallationError("destination-inside-source")
        relative, file_name = SOURCES[target]
        data = _read_source(root, relative)
        digest = hashlib.sha256(data).hexdigest()
        copy_action = {
            "action": "copy-file",
            "source": relative,
            "path": str(destination / file_name),
            "bytes": len(data),
            "sha256": digest,
        }
        plan = {
            "target": target,
            "status": "planned",
            "destination": str(destination),
            "actions": [
                {"action": "create-directory", "path": str(destination)},
                copy_action,
            ],
        }
        with _open_directory(destination.parent) as parent:
            _require_absent(parent, destination.name)
            if apply:
                _apply(parent, destination, file_name, data, digest)
                copy_action["verified_sha256"] = digest
                plan["status"] = "applied"
        return plan
    except InstallationError:
        raise
    except (OSError, ValueError, TypeError):
        # Do not print OS messages, source content, or unrelated paths.
        raise InstallationError("unsafe-or-unavailable-path") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=tuple(SOURCES))
    parser.add_argument("--destination", required=True, help="New absent directory; its parent must exist.")
    parser.add_argument("--apply", action="store_true", help="Explicitly approve copying this one adapter.")
    arguments = parser.parse_args(argv)
    try:
        result = install_adapter(arguments.target, arguments.destination, apply=arguments.apply)
    except InstallationError as error:
        print(json.dumps({"status": "refused", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
