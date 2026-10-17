#!/usr/bin/env python3
"""Offline, fail-closed audit of a release tree, not a guarantee of anonymity.

Reports contain only rule IDs, relative filenames and line numbers (0 for paths
or inspection failures). Sensitive filenames are redacted too. Only root .git
metadata and named build/cache directories are skipped; Git history is NOT
scanned and requires a dedicated history/secret scan before publication.
The optional denylist is an explicitly supplied external JSON array of strings;
never copy it into the release tree. No network access or filesystem writes.
Requires POSIX no-follow and descriptor-relative filesystem operations.
"""

import argparse
from contextlib import contextmanager
import ipaddress
import json
import os
from pathlib import Path
import re
import stat


MAX_FILE_BYTES = 1_048_576
MAX_TOTAL_BYTES = 64 * MAX_FILE_BYTES
MAX_ENTRIES = 20_000
MAX_DEPTH = 32
MAX_DENY_BYTES = 262_144
IGNORED_DIRS = frozenset({
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    ".venv", "venv", "node_modules", "build", "dist", "trial",
})
UNSAFE_DIRS = frozenset({
    "sessions", "backups", "logs", "memories", "history", "histories",
    "transcripts", "credentials", "secrets",
})
SAFE_HIDDEN_FILES = frozenset({".gitignore", ".gitattributes", ".editorconfig"})
UNSAFE_NAMES = frozenset({
    "auth.json", "credentials.json", "cookies.txt", "cookies.json",
    "backup.json", "sessions.json", "history.json", "memory.md",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "known_hosts",
    "authorized_keys", ".netrc", ".npmrc", ".pypirc",
})
UNSAFE_SUFFIX = re.compile(
    r"\.(?:db|sqlite\d*)(?:-(?:wal|shm|journal))?$|"
    r"\.(?:bak|backup|pem|key|p12|pfx|der|log|jsonl|sql|dump|"
    r"zip|tar|gz|tgz|bz2|xz|7z|rar|zst|whl|pyc)$", re.I
)
PATTERNS = (
    ("api-token", re.compile(
        r"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|"
        r"github_pat_[A-Za-z0-9_]{20,}|(?:AKIA|ASIA)[A-Z0-9]{16}|"
        r"xox[baprs]-[A-Za-z0-9-]{20,}|AIza[A-Za-z0-9_-]{35}|"
        r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}|"
        r"\d{6,12}:[A-Za-z0-9_-]{30,})\b"
    )),
    ("private-key", re.compile(r"-{5}BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-{5}")),
    ("ssh-key", re.compile(
        r"\b(?:ssh-(?:rsa|dss|ed25519)|ecdsa-sha2-[\w-]+)\s+[A-Za-z0-9+/]{32,}={0,3}"
    )),
    ("numeric-identifier", re.compile(
        r"\b(?:chat|user|channel|guild|account)[_-]?id[\"']?\s*[:=]\s*[\"']?-?\d{5,}\b|"
        r"(?<!\w)\+\d{1,3}(?:[ .()-]*\d){7,14}(?!\d)", re.I
    )),
)
EMAIL_LOCAL = r"A-Za-z0-9.!#$%&'*+/=?^_`{|}~-"
EMAIL = re.compile(r"(?<![" + EMAIL_LOCAL + r"])[" + EMAIL_LOCAL + r"]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
EXAMPLE_DOMAINS = ("example.com", "example.org", "example.net", "example.invalid", "example.test", "example.localhost")
HOST_PATH = re.compile(
    r"(?<![\w])(?:/(?:home|Users|mnt/data|root|srv|opt|media|Volumes|tmp)/|"
    r"[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/])([A-Za-z0-9_.-]+)"
)
PLACEHOLDERS = frozenset({"USER", "USERNAME", "PROJECT", "EXPORT", "PATH", "YOUR_USER", "your-user", "your-project"})
IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
IPV6 = re.compile(r"(?<![\w:])(?:[0-9a-f]{0,4}:){2,}[0-9a-f:.]{0,45}(?:%[\w.-]+)?(?![\w:])", re.I)
EXAMPLE_NETWORKS = tuple(map(ipaddress.ip_network, (
    "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "2001:db8::/32",
)))
ASSIGNMENT = re.compile(
    r"\b(?:[a-z0-9]{1,32}[_-]){0,4}(?:api[_-]?key|access[_-]?key|secret[_-]?key|"
    r"token|secret|password|passwd)[\"']?\s*[:=]\s*[\"']?([^\s\"'`,;{}\[\]<>]+)", re.I
)


class _Refused(Exception):
    """Internal static rule ID, never an underlying OS exception message."""


class _StopScan(Exception):
    pass


def _controls(text):
    return any((ord(c) < 32 and c not in "\t\r\n") or 127 <= ord(c) <= 159 for c in text)


def _absolute_path(value):
    raw = os.fspath(value)
    if not isinstance(raw, str) or not raw or _controls(raw) or any(c in raw for c in "\r\n\t"):
        raise ValueError
    path = Path(raw)
    if ".." in path.parts:
        raise ValueError
    return Path(os.path.abspath(path))  # Deliberately do not resolve symlinks.


def _directory_flags():
    return os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)


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


def _snapshot(metadata):
    return (metadata.st_dev, metadata.st_ino, metadata.st_mode, metadata.st_nlink,
            metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns)


def _read_regular_at(directory, name, limit=MAX_FILE_BYTES):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(name, flags, dir_fd=directory)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise _Refused("special-file")
        if not before.st_mode & 0o444:
            raise _Refused("unreadable-file")
        if before.st_size > limit:
            raise _Refused("file-too-large")
        chunks, length = [], 0
        while length <= limit:
            chunk = os.read(descriptor, min(65_536, limit + 1 - length))
            if not chunk:
                break
            chunks.append(chunk)
            length += len(chunk)
        after = os.fstat(descriptor)
        current = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if _snapshot(before) != _snapshot(after) or _snapshot(after) != _snapshot(current):
            raise _Refused("unreadable-file")
        if length > limit:
            raise _Refused("file-too-large")
        if length != before.st_size:
            raise _Refused("unreadable-file")
        return b"".join(chunks), after
    finally:
        os.close(descriptor)


def _load_denylist(root, deny_file):
    if deny_file is None:
        return ()
    path = _absolute_path(deny_file)
    if path == root or root in path.parents:
        raise ValueError
    with _open_directory(path.parent) as directory:
        data, _ = _read_regular_at(directory, path.name, MAX_DENY_BYTES)
    terms = json.loads(data.decode("utf-8"))
    if not isinstance(terms, list) or len(terms) > 512:
        raise ValueError
    for term in terms:
        if (not isinstance(term, str) or not term.strip() or len(term) > 512
                or not term.isprintable()):
            raise ValueError
    return tuple(sorted({term.casefold() for term in terms}))


def _content_rules(text, deny):
    rules = {rule for rule, pattern in PATTERNS if pattern.search(text)}
    folded = text.casefold() if deny else ""
    if any(term in folded for term in deny):
        rules.add("deny-term")
    for match in EMAIL.finditer(text):
        domain = match[1].lower().rstrip(".")
        if not any(domain == d or domain.endswith("." + d) for d in EXAMPLE_DOMAINS):
            rules.add("email")
    if any(match[1] not in PLACEHOLDERS for match in HOST_PATH.finditer(text)):
        rules.add("absolute-path")
    for pattern in (IPV4, IPV6):
        for match in pattern.finditer(text):
            try:
                address = ipaddress.ip_address(match[0])
            except ValueError:
                continue
            if not any(address.version == net.version and address in net for net in EXAMPLE_NETWORKS):
                rules.add("ip-address")
    for match in ASSIGNMENT.finditer(text):
        value = match[1].casefold()
        if (len(value) >= 8 and value not in {"placeholder", "redacted", "changeme", "example-value"}
                and not value.startswith(("os.getenv(", "os.environ", "${"))):
            rules.add("credential-assignment")
    return rules


def audit_release(root, *, deny_file=None):
    """Return deterministic, JSON-ready findings; [] means this bounded scan passed.

    The tree must be quiescent. Symlinks (including ancestors), hardlinks,
    runtime data, unreadable files and incomplete traversal fail closed. Build
    exclusions are not audited; neither are Git objects, refs or commit metadata.
    """
    findings = set()
    deny = ()
    entries = total_bytes = 0

    def add(relative, line, rule):
        # A sensitive identifier can occur in a filename as well as in its text.
        path = str(relative)
        safe = "[redacted]" if not path.isprintable() or _content_rules(path, deny) else path
        findings.add((safe, line, rule))

    def walk(directory, relative="", depth=0):
        nonlocal entries, total_bytes
        before = os.fstat(directory)
        names = []
        with os.scandir(directory) as iterator:
            for entry in iterator:
                entries += 1
                if entries > MAX_ENTRIES:
                    add(relative or ".", 0, "scan-limit")
                    raise _StopScan
                names.append(entry.name)
        for name in sorted(names):
            path = relative + "/" + name if relative else name
            metadata = None
            try:
                metadata = os.stat(name, dir_fd=directory, follow_symlinks=False)
                if stat.S_ISLNK(metadata.st_mode):
                    add(path, 0, "symlink")
                    continue
                for rule in _content_rules(path, deny):
                    add(path, 0, rule)
                lower = name.casefold()
                if stat.S_ISDIR(metadata.st_mode):
                    if ((not relative and name == ".git") or name in IGNORED_DIRS
                            or name.endswith(".egg-info")):
                        continue
                    if lower in UNSAFE_DIRS:
                        add(path, 0, "unsafe-directory")
                        continue
                    if name.startswith(".") and not (not relative and name == ".github"):
                        add(path, 0, "hidden-directory")
                        continue
                    if depth >= MAX_DEPTH:
                        add(path, 0, "scan-limit")
                        continue
                    child = os.open(name, _directory_flags(), dir_fd=directory)
                    try:
                        if _snapshot(metadata) != _snapshot(os.fstat(child)):
                            raise OSError
                        walk(child, path, depth + 1)
                        if _snapshot(metadata) != _snapshot(os.stat(name, dir_fd=directory, follow_symlinks=False)):
                            raise OSError
                    finally:
                        os.close(child)
                elif not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                    add(path, 0, "special-file")
                elif lower.startswith(".env") or lower in UNSAFE_NAMES or UNSAFE_SUFFIX.search(name):
                    add(path, 0, "unsafe-data-file")
                elif name.startswith(".") and name not in SAFE_HIDDEN_FILES:
                    add(path, 0, "hidden-file")
                elif metadata.st_size > MAX_FILE_BYTES:
                    add(path, 0, "file-too-large")
                else:
                    if total_bytes + metadata.st_size > MAX_TOTAL_BYTES:
                        add(path, 0, "scan-limit")
                        raise _StopScan
                    data, after = _read_regular_at(directory, name, MAX_FILE_BYTES)
                    total_bytes += len(data)
                    if _snapshot(metadata) != _snapshot(after):
                        raise _Refused("unreadable-file")
                    try:
                        text = data.decode("utf-8")
                    except UnicodeError:
                        raise _Refused("binary-or-non-utf8") from None
                    if _controls(text):
                        raise _Refused("binary-or-non-utf8")
                    for line_number, line in enumerate(text.splitlines(), 1):
                        for rule in _content_rules(line, deny):
                            add(path, line_number, rule)
            except _Refused as error:
                add(path, 0, str(error))
            except OSError:
                is_directory = metadata is not None and stat.S_ISDIR(metadata.st_mode)
                add(path, 0, "unreadable-directory" if is_directory else "unreadable-file")
        if _snapshot(before) != _snapshot(os.fstat(directory)):
            add(relative or ".", 0, "unreadable-directory")

    try:
        if (not all(hasattr(os, flag) for flag in ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK"))
                or os.open not in os.supports_dir_fd or os.stat not in os.supports_dir_fd
                or os.scandir not in os.supports_fd):
            raise ValueError
        root = _absolute_path(root)
        with _open_directory(root) as directory:
            try:
                deny = _load_denylist(root, deny_file)
            except (OSError, ValueError, TypeError, _Refused, RecursionError):
                add(".", 0, "deny-file-error")
                return [{"file": f, "line": n, "rule": r} for f, n, r in sorted(findings)]
            try:
                walk(directory)
                with _open_directory(root) as current:
                    if _snapshot(os.fstat(current)) != _snapshot(os.fstat(directory)):
                        raise OSError
            except _StopScan:
                pass
            except OSError:
                add(".", 0, "unreadable-directory")
    except (OSError, ValueError, TypeError):
        add(".", 0, "invalid-root")
    return [{"file": f, "line": n, "rule": r} for f, n, r in sorted(findings)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", metavar="ROOT", help="Release tree to inspect without following links.")
    parser.add_argument("--denylist", help="External JSON string array; never store it in the release tree.")
    parser.add_argument("--pretty", action="store_true", help="Indent the JSON findings.")
    args = parser.parse_args(argv)
    findings = audit_release(args.root, deny_file=args.denylist)
    print(json.dumps(findings, indent=2 if args.pretty else None, sort_keys=True))
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
