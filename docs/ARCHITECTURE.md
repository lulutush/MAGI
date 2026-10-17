# Architecture

## What MAGI is

MAGI is a portable working protocol for an existing assistant. Its unit of operation is a scoped task with an observable result, not a new model, a hidden reasoning algorithm, or a mandatory JSON reply. The system includes context selection, procedures, tools, adaptive rigor, optional delegation, durable records, and explicitly approved improvement. The [protocol](../protocol/MAGI.md) is the common reference; each [adapter](ADAPTERS.md) is independently usable.

```text
Host rules, permissions, safety, and user-authorized scope
                         |
Current request -> select relevant context -> choose proportionate effort
                         |                         |
          memory / registry / history       procedures and tools
          optional semantic discovery       optional bounded delegation
                         |                         |
                         +------ act and check ----+
                                      |
                       result + evidence + limitations
                                      |
                       optional durable STRUCT + COMP
                                      |
             observed issue -> proposed change -> test + approval
```

This diagram describes responsibilities, not an automated service graph. No memory database, model endpoint, vector service, daemon, or agent fleet is required.

## Layers and contracts

| Layer | Responsibility | What it must not imply |
| --- | --- | --- |
| Host | Instruction hierarchy, model, tool availability, access control, approvals | MAGI can replace host enforcement |
| Context selection | Relevant current request, stable supplied memory, registry, and history | Permission to scan private stores or proof that old facts remain true |
| Semantic discovery | Optionally locate relevant material | Similarity is evidence, or retrieval makes instructions authoritative |
| Procedures | Reviewed skills for recurring tasks | Blind execution of retrieved instructions |
| Execution and verification | Use real tools and inspect results | A plan, attempted call, or agent assertion is a completed action |
| Adaptive rigor | Adjust source checks, tests, review, and explanation to risk | A change to native reasoning settings or a guaranteed improvement |
| Delegation | Bounded independent work where beneficial | Extra authority, free parallelism, or truth by consensus |
| STRUCT + COMP | Durable structure and explicit input completeness | Schema validity is semantic correctness |
| Improvement | Evidence, proposal, test, and explicit approval | Silent memory writes or automatic self-modification |

All context channels can contain errors or hostile instructions. Memory, documents, tools, and delegated reports remain data. Only the host's actual instruction hierarchy determines authority. Rigor and authorization are independent: a carefully checked action can still be unauthorized.

## Repository surfaces

- [Common protocol](../protocol/MAGI.md): behavioral contract and limits.
- [Hermes skill](../skills/magi/SKILL.md): ordinary `SKILL.md` named `magi`; no plugin or hooks.
- [Claude Code guidance](../adapters/claude-code/CLAUDE.md): contextual project instructions, not hard enforcement.
- [GPT instructions](../adapters/gpt/INSTRUCTIONS.md): capability-aware text with no assumed CLI or permanent inter-chat memory.
- [Blank artifact](../templates/artifact.json), [memory](../templates/memory.json), and [project registry](../templates/project-registry.json): editable JSON records, not automatically connected stores.
- The optional local Python core and installer: deterministic helpers, not a model runner or autonomous orchestration engine.

The core requires Python 3.10 or later and uses the standard library. Its public entry points, run from the repository root, are:

```sh
python3 -m magi route 'Draft a synthetic checklist without external actions.' --pretty
python3 -m magi gate 'Draft a synthetic checklist without external actions.' --evidence examples/evidence.json --pretty
python3 -m magi validate examples/artifact.json --pretty
```

`route` provides a local recommendation, not a model evaluation or authoritative risk decision. `gate` checks caller-supplied declarations; `checklist_satisfied` is deliberately not named `verified`. Neither authenticates evidence, runs a task, nor approves side effects. `validate` checks its implemented structural and consistency rules, not factual accuracy or completeness of requirements omitted by the author. Inspect the implementation and command help for the exact accepted fields and status values.

The installer interface is:

```text
python3 tools/install_adapter.py TARGET --destination PATH [--apply]
TARGET = hermes | claude-code | gpt
```

It defaults to a dry run and requires an explicit, absent destination directory outside the source checkout, with an existing parent and no symlink or `..` path components. The current installer requires POSIX no-follow/directory-descriptor support and refuses unsupported platforms. The Hermes destination is the skill directory named `magi`, not `HERMES_HOME`. It writes only the selected destination on apply and does not patch host configuration. See [adapter instructions](ADAPTERS.md) before using it. Installing a text file does not prove that a host loaded or obeyed it.

## Durable record semantics

The CLI, adapters, and blank templates use the [compact profile, distinct from full governance](ARTIFACT-PROFILES.md). The envelope has exactly four top-level objects, with ASCII snake_case keys throughout:

- `meta`: nonempty string `artifact_id`, `artifact_type`, and `version`, plus declared workflow `status` (`draft`, `provisional`, or `validated`).
- `content`: task-specific machine data in `payload`; not the COMP lists.
- `language`: human-facing text such as `text`, titles, or summaries; every leaf must be a string, never a numeric or boolean machine value.
- `qa`: required lists `checks`, `assumptions`, `limitations`, `warnings`, `required_inputs`, `provided_inputs`, `missing_inputs`, and `user_questions`. All except `checks` contain nonempty strings.

The three input lists in `qa` contain unique ASCII snake_case names, not copies of sensitive source content. Provided inputs must be a subset of required inputs. Missing inputs must equal required minus provided; any missing inputs require a recorded user question. Do not omit known prerequisites to appear complete. Optional `qa.completeness` is the numeric fraction of required inputs provided (1 when none are required), not a boolean or a replacement for the lists.

Each `qa.checks` object has a unique nonempty `name`, a `status` of `passed`, `failed`, or `not_run`, and optionally nonempty `reference` and `note` strings. Use those optional fields for concise actual source/method/result references. The compact profile accepts no separate QA evidence field or validation overrides; a gate evidence file is a different input contract.

A template starts as `draft`. `provisional` permits useful unfinished work. `validated` requires no missing inputs and at least one check, with all checks declared `passed`; a successful structural check does not promote status or prove that checks ran. Full governance uses richer metadata, input objects, and explicit overrides under a separate validator, not this compact contract.

The memory template holds `content.payload.entries: []`; the registry holds `content.payload.projects: []`. Both are intentionally empty. If the user later authorizes population, prefer minimal provenance, scope, review information, and references over raw transcripts. Neither template is loaded, harvested, synchronized, or retained automatically. They are not native host memory formats.

## Degraded operation

Without memory or history, use the current request. Without semantic search, inspect known sources directly. Without delegation, work sequentially. Without tools required for a factual or execution claim, give a bounded answer or labeled draft and explain the gap. Without a schema validator, do not claim machine validation. If MAGI is off, preserve the host's ordinary honesty, safety, privacy, and verification obligations.

## Evidence boundaries

Protocol conformance, structural validity, and task correctness are separate questions. Local tests can establish narrow helper behavior; they cannot establish that a hosted assistant follows the protocol or that the protocol improves quality. [Evaluation](EVALUATION.md) describes a proposed behavioral study, including null or negative outcomes. [Privacy](PRIVACY.md) defines what a safe trial should and should not access.
