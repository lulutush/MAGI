#!/usr/bin/env python3
"""Mechanical full-envelope check; not factual verification or authorization."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import re

ROOT_KEYS = ["meta", "content", "language", "qa"]
META_FIELDS = ["project_code", "artifact_id", "artifact_type", "scope", "status", "version", "created_at", "updated_at"]
QA_LISTS = ["checks", "assumptions", "limitations", "warnings", "required_inputs", "provided_inputs", "missing_inputs", "user_questions"]
STATUSES = {"draft", "provisional", "validated", "deprecated", "superseded"}
SEVERITIES = {"blocking", "important", "nice_to_have"}


def text(value):
    return isinstance(value, str) and bool(value.strip())


def timestamp(value):
    if not text(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None
    except ValueError:
        return False


def validate(value):
    errors = []
    if not isinstance(value, dict) or list(value) != ROOT_KEYS:
        return ["root_keys_must_be_ordered_meta_content_language_qa"]
    if not all(isinstance(value[key], dict) for key in ROOT_KEYS):
        return ["root_blocks_must_be_objects"]
    def check_keys(item, depth=0):
        if depth > 80:
            errors.append("excessive_nesting")
            return
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", key):
                    errors.append("keys_must_be_ascii_snake_case")
                check_keys(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                check_keys(child, depth + 1)
        elif isinstance(item, float) and not math.isfinite(item):
            errors.append("non_finite_number")
    check_keys(value)
    meta, content, language, qa = (value[key] for key in ROOT_KEYS)
    for field in META_FIELDS:
        if not text(meta.get(field)):
            errors.append("missing_or_invalid_meta_" + field)
    status = meta.get("status")
    if not isinstance(status, str) or status not in STATUSES:
        errors.append("invalid_status")
    if not text(meta.get("standard_id")) and not text(meta.get("magistral_id")):
        errors.append("missing_standard_identity")
    for field in ["created_at", "updated_at"]:
        if not timestamp(meta.get(field)):
            errors.append("invalid_" + field)
    source = meta.get("source")
    if (not isinstance(source, dict) or not text(source.get("type")) or
            not isinstance(source.get("references"), list) or
            not all(text(x) for x in source.get("references", []))):
        errors.append("invalid_structured_source")
    if not content:
        errors.append("content_empty")
    if not language:
        errors.append("language_empty")
    for field in QA_LISTS:
        if not isinstance(qa.get(field), list):
            errors.append("missing_or_invalid_qa_" + field)
    if errors:
        return list(dict.fromkeys(errors))

    def inputs(items, label):
        result = {}
        for item in items:
            if not isinstance(item, dict) or not text(item.get("name")) or not text(item.get("reason")):
                errors.append("invalid_" + label + "_input")
                continue
            severity = item.get("severity")
            if not isinstance(severity, str) or severity not in SEVERITIES:
                errors.append("invalid_" + label + "_severity")
                continue
            name = item["name"]
            if name in result:
                errors.append("duplicate_" + label + "_input")
            result[name] = item
        return result
    required = inputs(qa["required_inputs"], "required")
    missing = inputs(qa["missing_inputs"], "missing")
    provided = qa["provided_inputs"]
    if not all(text(x) for x in provided):
        errors.append("provided_inputs_must_be_names")
        provided_set = set()
    else:
        provided_set = set(provided)
        if len(provided_set) != len(provided):
            errors.append("duplicate_provided_input")
    if not provided_set <= set(required):
        errors.append("provided_input_not_declared")
    if set(missing) != set(required) - provided_set:
        errors.append("missing_inputs_do_not_reconcile")
    for name, item in missing.items():
        if name in required and item["severity"] != required[name]["severity"]:
            errors.append("missing_input_severity_changed")
    accepted = qa.get("accepted_missing_inputs", [])
    if not isinstance(accepted, list):
        errors.append("accepted_inputs_must_be_list")
        accepted = []
    accepted_names = set()
    for item in accepted:
        if (not isinstance(item, dict) or not all(text(item.get(k)) for k in
                ["name", "accepted_by", "acceptance_note", "impact"]) or
                not timestamp(item.get("acceptance_timestamp"))):
            errors.append("invalid_acceptance_record")
            continue
        name = item["name"]
        if name in accepted_names or name not in missing:
            errors.append("duplicate_or_unknown_accepted_input")
        accepted_names.add(name)
    questions = set()
    for item in qa["user_questions"]:
        if not isinstance(item, dict) or not text(item.get("input_name")) or not text(item.get("question")):
            errors.append("invalid_question_record")
        else:
            questions.add(item["input_name"])
    unresolved = {name for name, item in missing.items()
                  if item["severity"] in {"blocking", "important"}} - accepted_names
    if not unresolved <= questions:
        errors.append("unresolved_inputs_need_questions")
    checks = qa["checks"]
    for item in checks:
        if not isinstance(item, dict) or not text(item.get("name")) or type(item.get("passed")) is not bool:
            errors.append("invalid_check_record")
    if status == "validated":
        if unresolved:
            errors.append("validated_has_unaccepted_missing_inputs")
        if not checks or any(not isinstance(x, dict) or x.get("passed") is not True for x in checks):
            errors.append("validated_requires_passing_declared_checks")
    return list(dict.fromkeys(errors))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def invalid_constant(_value):
    raise ValueError("non-finite JSON number")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        with args.file.open("rb") as handle:
            data = handle.read(1024 * 1024 + 1)
        if len(data) > 1024 * 1024:
            raise ValueError("input too large")
        value = json.loads(data.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=invalid_constant)
        errors = validate(value)
    except (OSError, ValueError, RecursionError):
        errors = ["unreadable_or_invalid_json_input"]
    print(json.dumps({"structure_valid": not errors, "errors": errors,
                      "independent_verification": False, "authorization_granted": False}, indent=2))
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
