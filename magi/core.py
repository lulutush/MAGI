"""Portable, deterministic MAGI routing and declarative checks.

Only the standard library is used. The core performs no I/O, tool calls, model
calls, telemetry or persistence. Routes are bounded-keyword EN/FR heuristics,
not semantic classification, calibrated confidence, permission or enforcement.

The gate checks caller-supplied records, not the truth/authenticity of evidence.
Reference strings are opaque data: they are never fetched, interpreted or echoed.
Neither the route nor the gate can change the host's instruction hierarchy.

The intentionally small STRUCT+COMP profile uses four object blocks:
* meta: nonempty artifact_id, artifact_type, version; status is draft,
  provisional or validated. Additional JSON metadata is allowed.
* content: JSON-compatible machine data with finite numbers.
* language: objects/lists containing text leaves only.
* qa: checks (name/status, optional reference/note), assumptions, limitations,
  warnings, required_inputs, provided_inputs, missing_inputs, user_questions.
  Input collections are unique ASCII snake_case strings. Provided inputs must
  be declared as required; missing must equal required minus provided.
  Optional completeness is a number in [0, 1], equal to the provided fraction.
Validated requires no missing inputs and at least one check, all passed. This
profile intentionally has no override mechanism. It checks declared consistency,
not domain completeness or factual correctness. Object order is not significant.
"""
from __future__ import annotations

import math
import re
import unicodedata


PROFILES = ("magi_none", "magi_light", "magi_standard", "magi_strict", "magi_audit")
EVIDENCE_KEYS = (
    "live_observation", "source_read", "history_read", "artifact_checked",
    "authorization_checked", "action_verified",
)
_ROUTE_SCHEMA = "magi.route.v1"
_KEY = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*\Z")
_MAX_DEPTH = 64

# Explicit whole tokens/phrases, not stemming or substring matching. False
# positives (including negation/quoted requests) and false negatives are possible.
_TERMS = {
    "simple": (
        "hello", "hi", "bonjour", "salut", "thanks", "merci", "translate",
        "translation", "traduis", "traduire", "rephrase", "reformule",
        "reformuler", "short message", "message court", "corrige ce texte",
        "summarize", "summarise", "resume", "resumer",
    ),
    "high_risk": (
        "audit", "security", "securite", "risk", "risks", "risque", "risques",
        "production", "firewall", "pare feu", "ssh", "tls", "certificate",
        "certificat", "port", "ports", "credentials", "password", "passwords",
        "mot de passe", "secret", "secrets", "token", "jeton", "vulnerability",
        "vulnerabilite", "breach", "financial", "financier", "finance",
        "medical", "medicale", "legal", "juridique", "payment", "paiement",
        "delete", "deletion", "suppression", "supprime", "supprimer", "wipe",
        "efface", "effacer", "publish", "publie", "publication",
        "verite absolue", "absolute truth",
    ),
    "live": (
        "current", "currently", "latest", "now", "today", "recent", "recently",
        "actuel", "actuelle", "actuellement", "aujourd hui", "maintenant",
        "recente", "derniere version", "what time", "current time", "heure",
        "date", "weather", "meteo", "news", "actualite", "actualites",
        "process", "processes", "processus", "cpu", "ram", "disk", "disque",
        "memory usage", "utilisation memoire", "git", "cron", "service status",
        "etat du service", "running", "en cours d execution",
    ),
    "history": (
        "history", "historical", "historique", "previous conversation",
        "previous decision", "past conversation", "earlier decision",
        "last time", "what did we decide", "where did we leave",
        "conversation precedente", "decision precedente", "ancienne decision",
        "dernier echange", "ou en etions", "ou en sommes", "souviens",
    ),
    "source": (
        "document", "documents", "source", "sources", "file", "files",
        "fichier", "fichiers", "pdf", "attachment", "piece jointe", "read",
        "lis", "lire", "extract", "extrait", "extraction", "reference",
    ),
    "project": (
        "project", "projects", "projet", "projets", "architecture", "system",
        "systeme", "workflow", "configuration", "config", "service",
        "analysis", "analyse", "analyze", "analysez", "orchestration",
    ),
    "create": (
        "create", "creating", "cree", "creer", "build", "construis",
        "construire", "write", "writing", "ecris", "ecrire", "redige",
        "rediger", "generate", "genere", "generer", "produce", "produis",
        "produire", "implement", "implemente", "implementer", "export",
        "exporte", "exporter",
    ),
    "artifact": (
        "artifact", "artifacts", "artefact", "artefacts", "json", "struct comp",
        "file", "fichier", "report", "rapport", "policy", "politique",
        "standard", "dataset", "jeu de donnees", "schema", "specification",
        "workflow", "procedure", "script", "code", "configuration",
        "deliverable", "livrable",
    ),
    "reuse": ("reusable", "reutilisable", "durable", "deliverable", "livrable", "struct comp"),
    "effect": (
        "delete", "deletes", "deleting", "remove", "removes", "removing",
        "supprime", "supprimer", "efface", "effacer", "wipe", "destroy",
        "detruis", "detruire", "disable", "desactive", "desactiver", "enable",
        "active", "activer", "activate", "configure", "configurer", "change",
        "modify", "modifie", "modifier", "update", "mettre a jour",
        "send", "envoie", "envoyer", "publish", "publie", "publier", "deploy",
        "deploie", "deployer", "install", "installe", "installer", "restart",
        "redemarre", "redemarrer", "execute", "executer", "run", "lance",
        "lancer", "pay", "paie", "payer", "purchase", "achete", "acheter",
        "grant", "revoke", "revoque", "revoquer", "upload", "televerse",
    ),
    "mutable_target": (
        "file", "files", "fichier", "fichiers", "directory", "folder",
        "dossier", "repertoire", "account", "compte", "database", "base de donnees",
        "server", "serveur", "service", "configuration", "config",
    ),
    "complex": (
        "complex", "complexe", "multi agent", "multiple agents", "plusieurs agents",
        "subagents", "sub agents", "refonte", "end to end", "de bout en bout",
        "full architecture", "architecture complete", "independent workstreams",
    ),
    "validate": ("validate", "validation", "valide", "valider"),
}


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^\w]+", " ", folded).split())


_PATTERNS = {
    group: tuple((term, re.compile(r"(?<!\w)" + re.escape(_normalize(term)) + r"(?!\w)")) for term in terms)
    for group, terms in _TERMS.items()
}
_REQUIREMENT_FIELDS = (
    ("live_observation", "tool_policy", "verify_live_state"),
    ("source_read", "context_policy", "source_read_required"),
    ("history_read", "context_policy", "history_read_required"),
    ("artifact_checked", "artifact_policy", "status_gate_required"),
    ("authorization_checked", "action_policy", "authorization_required"),
    ("action_verified", "action_policy", "verification_after_action_required"),
)
_CAPABILITIES = {
    "live_observation": "current_state_reader",
    "source_read": "source_reader",
    "history_read": "history_reader",
    "artifact_checked": "artifact_validator",
    "authorization_checked": "host_authorization_review",
    "action_verified": "post_action_verifier",
}


def _requirements(decision: dict) -> list[str]:
    """Reject malformed caller decisions rather than defaulting to no checks."""
    if type(decision) is not dict:
        raise TypeError("decision must be a route dictionary")
    if decision.get("schema") != _ROUTE_SCHEMA or decision.get("profile") not in PROFILES:
        raise ValueError("decision must use the MAGI route schema and a known profile")
    required = []
    for name, section, flag in _REQUIREMENT_FIELDS:
        policy = decision.get(section)
        if type(policy) is not dict or type(policy.get(flag)) is not bool:
            raise ValueError(f"decision.{section}.{flag} must be a boolean")
        if policy[flag]:
            required.append(name)
    action = decision["action_policy"]
    if type(action.get("side_effects_requested")) is not bool:
        raise ValueError("decision.action_policy.side_effects_requested must be a boolean")
    if action["side_effects_requested"] and not {
        "live_observation", "source_read", "authorization_checked", "action_verified"
    }.issubset(required):
        raise ValueError("side-effect decisions require context, authorization and before/after observations")
    return required


def route(query: str) -> dict:
    """Return a fresh, JSON-compatible advisory route without reading any state.

    High-risk and side-effect signals take precedence over simple requests.
    Instructions embedded in the query are classified as text, never executed.
    The caller must still apply host policies and actual human authorization.
    """
    if type(query) is not str:
        raise TypeError("query must be a string")
    normalized = _normalize(query)
    if not normalized:
        raise ValueError("query must contain nonempty text")
    hits = {
        group: [term for term, pattern in patterns if pattern.search(normalized)]
        for group, patterns in _PATTERNS.items()
    }
    side_effects = bool(hits["effect"] or (hits["create"] and hits["mutable_target"]))
    high_risk = bool(hits["high_risk"])
    durable = bool(hits["artifact"] and (hits["create"] or hits["reuse"] or hits["validate"] or hits["effect"]))
    live = bool(hits["live"] or high_risk or side_effects)
    historical = bool(hits["history"])
    source = bool(hits["source"] or hits["project"] or durable or high_risk or side_effects)
    complex_task = bool(hits["complex"])
    if high_risk or side_effects:
        profile, task = "magi_audit", "audit"
    elif durable:
        profile, task = "magi_strict", "artifact"
    elif live or source or historical or complex_task or hits["artifact"]:
        profile = "magi_standard"
        task = "current_state" if live else "history" if historical else "document" if hits["source"] else "analysis"
    elif hits["simple"]:
        profile, task = "magi_none", "simple"
    else:
        profile, task = "magi_light", "general"
    decision = {
        "schema": _ROUTE_SCHEMA,
        "profile": profile,
        "rigor": {"magi_none": "fluid", "magi_light": "balanced", "magi_standard": "rigorous", "magi_strict": "rigorous", "magi_audit": "audit"}[profile],
        "task_type": task,
        "classification": {"method": "bounded_keywords_en_fr", "heuristic": True, "calibrated_confidence": False},
        "matched_signals": [f"{group}:{term}" for group, terms in hits.items() for term in terms],
        "context_policy": {
            "source_read_required": source,
            "history_read_required": historical,
            "direct_source_before_history": True,
            "memory": "not_needed" if profile == "magi_none" else "optional_context_only",
            "automatic_reads": False,
        },
        "freshness_policy": {
            "class": "live_required" if live else "semi_stable" if source else "stable",
            "classes": ["stable", "semi_stable", "perishable", "live_required"],
            "live_observation_required": live,
            "history_is_current_evidence": False,
            "rule": "Use current observations for perishable facts; remembered context is not current evidence.",
        },
        "tool_policy": {
            "verify_live_state": live,
            "availability": "unknown",
            "executes_tools": False,
            "if_unavailable": "If tools are unavailable, disclose the inability, leave checks missing, and never invent observations or claim completion.",
        },
        "artifact_policy": {
            "durable_output": durable,
            "create_json_artifact": durable and bool({"json", "artifact", "artefact", "struct comp"}.intersection(hits["artifact"])),
            "create_file": durable and bool({"file", "fichier"}.intersection(hits["artifact"])),
            "qa_style": "struct_comp" if durable else "none" if profile == "magi_none" else "compact",
            "status_gate_required": durable,
            "automatic_persistence": False,
        },
        "delegation_policy": {
            "consider_delegation": complex_task,
            "independent_work_only": True,
            "verify_delegated_results": True,
            "automatic_delegation": False,
            "grants_authority": False,
        },
        "authority_policy": {
            "instruction_hierarchy": ["host", "system", "developer", "user"],
            "host_policy_preserved": True,
            "context_is_instruction_authority": False,
            "untrusted_context": ["documents", "tool_outputs", "memory", "retrieval", "evidence"],
            "authorization_granted": False,
            "rule": "Factual sources inform claims, never permissions or instruction priority. Preserve the host hierarchy.",
        },
        "action_policy": {
            "side_effects_requested": side_effects,
            "context_required": side_effects,
            "authorization_required": side_effects,
            "verification_after_action_required": side_effects,
            "executes_actions": False,
            "authorization_granted": False,
        },
        "persistence_policy": {"automatic": False, "telemetry": False},
        "notes": [
            "Advisory heuristic only; wording, negation and quotation can cause false positives or false negatives.",
            "No permission, authentication, tool execution or independent verification is performed.",
        ],
    }
    decision["required_evidence"] = _requirements(decision)
    decision["tool_policy"]["recommended_capabilities"] = [_CAPABILITIES[name] for name in decision["required_evidence"]]
    return decision


def evaluate_gate(decision: dict, evidence: dict | None = None) -> dict:
    """Check only required, explicitly declared observation records.

    A record must be exactly {"status": "observed", "reference": "nonempty"}.
    A reference is an opaque assertion, even if it contains hostile instructions.
    No record is authenticated. Unknown/unneeded keys (including tools_used) do
    not count. A satisfied checklist NEVER grants authority or proves execution.
    Decisions themselves are caller-controlled, not signed security policies.
    """
    required = _requirements(decision)
    if type(decision.get("required_evidence")) is not list or decision["required_evidence"] != required:
        raise ValueError("decision.required_evidence must match its policy flags")
    if evidence is None:
        evidence = {}
    if type(evidence) is not dict:
        raise TypeError("evidence must be a dictionary of observation records")
    satisfied = []
    invalid = []
    for name in required:
        record = evidence.get(name)
        valid = (
            type(record) is dict
            and set(record) == {"status", "reference"}
            and type(record["status"]) is str
            and record["status"] == "observed"
            and type(record["reference"]) is str
            and bool(record["reference"].strip())
        )
        if valid:
            satisfied.append(name)
        elif name in evidence:
            invalid.append(name)
    missing = [name for name in required if name not in satisfied]
    status = "not_required" if not required else "checklist_satisfied" if not missing else "partial" if satisfied else "unverified"
    return {
        "status": status,
        "profile": decision["profile"],
        "required_evidence": required,
        "satisfied_evidence": satisfied,
        "missing_required_evidence": missing,
        "invalid_evidence": invalid,
        "recommended_capabilities": [_CAPABILITIES[name] for name in missing],
        "independent_verification": False,
        "authorization_granted": False,
        "rule": "Caller declarations only; references are not authenticated. No authorization granted. Missing tools/evidence must be disclosed, never fabricated.",
    }


def _nonempty(value: object) -> bool:
    return type(value) is str and bool(value.strip())


def _json_errors(value: object) -> list[str]:
    """Validate JSON types, ASCII key conventions, depth and finite numbers."""
    errors: list[str] = []
    ancestors: set[int] = set()

    def walk(item: object, path: str, depth: int) -> None:
        if depth > _MAX_DEPTH:
            errors.append(f"{path}: exceeds maximum nesting depth {_MAX_DEPTH}")
            return
        kind = type(item)
        if kind in (dict, list):
            identity = id(item)
            if identity in ancestors:
                errors.append(f"{path}: cyclic values are not JSON")
                return
            ancestors.add(identity)
            if type(item) is dict:
                for key, child in item.items():
                    if type(key) is not str or not _KEY.fullmatch(key):
                        errors.append(f"{path}: keys must be ASCII snake_case strings")
                    walk(child, f"{path}.{key}" if type(key) is str and _KEY.fullmatch(key) else f"{path}.<invalid_key>", depth + 1)
            elif type(item) is list:
                for index, child in enumerate(item):
                    walk(child, f"{path}[{index}]", depth + 1)
            ancestors.remove(identity)
        elif type(item) is float:
            if not math.isfinite(item):
                errors.append(f"{path}: numbers must be finite")
        elif type(item) is str:
            try:
                item.encode("utf-8")
            except UnicodeEncodeError:
                errors.append(f"{path}: text must contain valid Unicode characters")
        elif item is not None and kind not in (bool, int):
            errors.append(f"{path}: unsupported non-JSON value")

    walk(value, "$", 0)
    return errors


def _string_list(value: object, path: str, errors: list[str], *, names: bool = False) -> list[str] | None:
    if type(value) is not list:
        errors.append(f"{path}: must be an array of nonempty strings")
        return None
    if any(not _nonempty(item) for item in value):
        errors.append(f"{path}: every item must be a nonempty string")
        return None
    if names:
        if any(not _KEY.fullmatch(item) for item in value):
            errors.append(f"{path}: input names must be ASCII snake_case")
        if len(set(value)) != len(value):
            errors.append(f"{path}: names must be unique")
    return value


def validate_artifact(value: object) -> list[str]:
    """Return deterministic structural errors, or [] for declared consistency.

    This is a generic profile, not a truth verifier or a domain-specific catalog.
    Booleans are JSON booleans, never numbers for the optional completeness ratio.
    Invalid JSON-like types, cycles and excessive depth return errors, not success.
    """
    errors = _json_errors(value)
    if errors:
        return errors
    if type(value) is not dict:
        return ["$: artifact must be an object"]
    blocks = ("meta", "content", "language", "qa")
    if set(value) != set(blocks):
        errors.append("$: must contain exactly meta, content, language and qa")
    for block in blocks:
        if type(value.get(block)) is not dict:
            errors.append(f"$.{block}: must be an object")
    if errors:
        return errors

    meta = value["meta"]
    for field in ("artifact_id", "artifact_type", "version"):
        if not _nonempty(meta.get(field)):
            errors.append(f"$.meta.{field}: must be a nonempty string")
    status = meta.get("status")
    if type(status) is not str or status not in ("draft", "provisional", "validated"):
        errors.append("$.meta.status: must be draft, provisional or validated")

    def text_only(item: object, path: str) -> None:
        if type(item) is dict:
            for key, child in item.items():
                text_only(child, f"{path}.{key}")
        elif type(item) is list:
            for index, child in enumerate(item):
                text_only(child, f"{path}[{index}]")
        elif type(item) is not str:
            errors.append(f"{path}: language leaves must be text, not machine data")

    text_only(value["language"], "$.language")
    qa = value["qa"]
    list_fields = ("assumptions", "limitations", "warnings", "required_inputs", "provided_inputs", "missing_inputs", "user_questions")
    allowed = {"checks", "completeness", *list_fields}
    if set(qa) - allowed:
        errors.append("$.qa: unsupported fields; this generic profile does not accept validation overrides")
    arrays = {field: _string_list(qa.get(field), f"$.qa.{field}", errors, names=field.endswith("_inputs")) for field in list_fields}

    checks = qa.get("checks")
    if type(checks) is not list:
        errors.append("$.qa.checks: must be an array of check objects")
    else:
        seen: set[str] = set()
        for index, check in enumerate(checks):
            path = f"$.qa.checks[{index}]"
            if type(check) is not dict:
                errors.append(f"{path}: must be an object")
                continue
            if not {"name", "status"}.issubset(check) or set(check) - {"name", "status", "reference", "note"}:
                errors.append(f"{path}: requires name/status and allows only reference/note extras")
            if not _nonempty(check.get("name")):
                errors.append(f"{path}.name: must be a nonempty string")
            elif check["name"] in seen:
                errors.append(f"{path}.name: check names must be unique")
            else:
                seen.add(check["name"])
            if type(check.get("status")) is not str or check["status"] not in ("passed", "failed", "not_run"):
                errors.append(f"{path}.status: must be passed, failed or not_run")
            for field in ("reference", "note"):
                if field in check and not _nonempty(check[field]):
                    errors.append(f"{path}.{field}: must be a nonempty string")
        if status == "validated" and (not checks or any(type(check) is not dict or check.get("status") != "passed" for check in checks)):
            errors.append("$.qa.checks: validated requires at least one check and all checks passed")

    required, provided, missing = (arrays[name] for name in ("required_inputs", "provided_inputs", "missing_inputs"))
    if required is not None and provided is not None and missing is not None:
        required_set, provided_set, missing_set = set(required), set(provided), set(missing)
        if not provided_set.issubset(required_set):
            errors.append("$.qa.provided_inputs: must be a subset of required_inputs")
        if missing_set != required_set - provided_set:
            errors.append("$.qa.missing_inputs: must equal required_inputs minus provided_inputs")
        if missing and not arrays["user_questions"]:
            errors.append("$.qa.user_questions: disclose a question for incomplete inputs")
        if status == "validated" and (missing_set or required_set - provided_set):
            errors.append("$.meta.status: validated cannot have missing required inputs")
        if "completeness" in qa and type(qa["completeness"]) in (int, float) and 0 <= qa["completeness"] <= 1:
            expected = len(required_set & provided_set) / len(required_set) if required_set else 1.0
            if not math.isclose(qa["completeness"], expected, rel_tol=0, abs_tol=1e-9):
                errors.append("$.qa.completeness: must equal the fraction of required inputs provided")
    if "completeness" in qa:
        completeness = qa["completeness"]
        if type(completeness) not in (int, float) or not 0 <= completeness <= 1:
            errors.append("$.qa.completeness: must be a finite number in [0, 1], not a boolean")
    return errors
