"""Explicit, local-only JSON CLI for the portable MAGI core.

Only user-supplied evidence/artifact paths are read. No automatic discovery,
configuration loading, network requests, environment lookup or persistence.
Exit 0 means a route, a satisfied/not-required checklist, or structural validity;
exit 2 means incomplete evidence, invalid input or invalid declared structure.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from . import __version__, evaluate_gate, route, validate_artifact


_MAX_INPUT_BYTES = 1024 * 1024


def _reject_constant(value: str) -> None:
    raise ValueError("JSON numbers must be finite; NaN and Infinity are not accepted")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("JSON numbers must be finite")
    return number


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON objects must not contain duplicate keys")
        result[key] = value
    return result


def _read_json(path: str) -> object:
    """Read one explicitly requested UTF-8 JSON file with conservative bounds."""
    with Path(path).open("rb") as stream:
        raw = stream.read(_MAX_INPUT_BYTES + 1)
    if len(raw) > _MAX_INPUT_BYTES:
        raise ValueError("JSON input exceeds the 1 MiB limit")
    return json.loads(
        raw.decode("utf-8"), parse_constant=_reject_constant,
        parse_float=_finite_float, object_pairs_hook=_unique_object,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MAGI advisory routing and declarative JSON checks (EN/FR).")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    route_parser = commands.add_parser("route", help="Classify a request using bounded EN/FR keywords")
    route_parser.add_argument("query")
    gate_parser = commands.add_parser("gate", help="Check evidence declarations; never authenticate or authorize")
    gate_parser.add_argument("query")
    gate_parser.add_argument("--evidence", metavar="PATH", help="Explicit local JSON file with observation records")
    validate_parser = commands.add_parser("validate", help="Check generic STRUCT+COMP declared consistency")
    validate_parser.add_argument("path", metavar="PATH")
    for command_parser in (route_parser, gate_parser, validate_parser):
        command_parser.add_argument("--pretty", action="store_true", help="Indent JSON output")
    args = parser.parse_args(argv)
    try:
        if args.command == "route":
            result, code = route(args.query), 0
        elif args.command == "gate":
            decision = route(args.query)
            evidence = _read_json(args.evidence) if args.evidence is not None else None
            # An explicit JSON null is invalid input, not omitted evidence.
            if type(evidence) is not dict and evidence is not None:
                raise ValueError("evidence JSON must be an object")
            if args.evidence is not None and evidence is None:
                raise ValueError("evidence JSON must be an object")
            result = evaluate_gate(decision, evidence)
            code = 0 if result["status"] in ("checklist_satisfied", "not_required") else 2
        else:
            errors = validate_artifact(_read_json(args.path))
            result = {"valid": not errors, "errors": errors, "independent_verification": False, "scope": "declared_structure_and_completeness_only"}
            code = 2 if errors else 0
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError) as error:
        if isinstance(error, RecursionError):
            message = "JSON input is nested too deeply"
        elif isinstance(error, UnicodeError):
            message = "JSON input must be valid UTF-8"
        elif isinstance(error, json.JSONDecodeError):
            message = f"Invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}"
        elif isinstance(error, OSError):
            message = "Cannot read the explicitly requested JSON file"
        else:
            message = str(error)
        result, code = {"error": "invalid_input", "message": message}, 2
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2 if args.pretty else None))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
