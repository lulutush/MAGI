# MAGI

**A portable reliability protocol for AI assistants — context, tools, evidence, and adaptive rigor.**

[Français](README.fr.md) · [Protocol](protocol/MAGI.md) · [Adapters](docs/ADAPTERS.md) · [Evaluation](docs/EVALUATION.md)

**Status: experimental open-source distribution under Apache 2.0.** No hosted service, account, API credential, or private memory is bundled. See the [release checklist](docs/PUBLICATION.md).

## What it is

MAGI helps an assistant decide **when to answer directly, retrieve context, use tools, verify, structure an artifact, ask a question, or delegate**. It combines a concise operating protocol with a small offline reference implementation.

It is not a new model, an accuracy guarantee, a permissions system, or an automatic replacement for a host agent. Instruction files influence model behavior; they do not enforce security. A deterministic checklist checks declarations, not the truth of the underlying evidence.

The goal is the **lightest reliable path**, not maximum ceremony. Native model reasoning effort and MAGI rigor are separate settings. Simple work should remain simple.

## Try it without installing anything

Python 3.10+ is the only runtime dependency. Clone the repository first:

```sh
git clone https://github.com/lulutush/MAGI.git
cd MAGI
```

From this directory:

```sh
python3 -m magi --version
python3 -m magi route "Review a deployment plan before any changes" --pretty
python3 -m magi validate examples/artifact.json --pretty
python3 -m unittest discover -s tests -v
```

These commands do not call an LLM, access the network, read your credentials, or collect your memories. They run the reference implementation, not a measurement of model answer quality.

A missing-evidence example (exit code 2 is expected):

```sh
python3 -m magi gate "Check the current server status" --pretty
```

`route` is an English/French keyword heuristic, **not a security classifier**. Unknown wording can be missed. The agent and host permissions must still assess the actual request. `gate` returns a declared-checklist result and never grants permission to execute an action.

## Choose your host

- **Hermes Agent:** install the self-contained [MAGI skill](skills/magi/SKILL.md) into an explicitly selected skill directory, then load it with `/skill magi`. No gateway plugin or config mutation is included.
- **Claude Code:** use the standalone [CLAUDE.md adapter](adapters/claude-code/CLAUDE.md) in a new test project. Merge manually if the project already has instructions; do not overwrite them.
- **GPT / ordinary chat:** copy [INSTRUCTIONS.md](adapters/gpt/INSTRUCTIONS.md) into a GPT's instructions or a new chat. Tools and persistence exist only if the host actually provides them. Uploading Python files does not install or execute them.

### Safe local preparation

The adapter installer **previews by default**. It requires an explicit, new destination and refuses replacement of existing files/directories and symlink paths.

```sh
TRIAL_PARENT="$(mktemp -d)"
python3 tools/install_adapter.py hermes --destination "$TRIAL_PARENT/magi"
python3 tools/install_adapter.py hermes --destination "$TRIAL_PARENT/magi" --apply
python3 tools/install_adapter.py claude-code --destination "$TRIAL_PARENT/claude-project"
python3 tools/install_adapter.py gpt --destination "$TRIAL_PARENT/gpt-text"
```

These paths must be absent directories under an existing, symlink-free parent outside the checkout. The safe-copy installer requires POSIX support; the Python core itself is platform-independent. The default is **dry-run**. `--apply` copies an adapter only to the explicitly selected destination, refuses existing targets and symlinks, and verifies written bytes. It does not change a live profile, patch a configuration, or start a model. Host loading and model behavior require separate tests; no live-host test is claimed here.

## What ships

- `protocol/`: the host-neutral method.
- `magi/`: offline routing, evidence checklists, and artifact validation.
- `skills/`, `adapters/`: standalone host instruction files.
- `templates/`: empty context/registry/artifact templates, not collected user data.
- `governance/`: the optional fuller STRUCT+COMP envelope and its offline validator; see [artifact profiles](docs/ARTIFACT-PROFILES.md).
- `examples/`: explicitly synthetic examples.
- `tests/`: deterministic checks; not an LLM benchmark.
- `tools/`: destination-explicit installer, release audit, allowlisted archive builder.
- `docs/`: scope, privacy, evaluation protocol, and publication checklist.

The public core keeps the distinction between **stable preferences, project state, historical context, procedural skills, evidence, and explicit authority**. The host owns its own storage. There is no bundled semantic database, private artifact store, conversation archive, scheduled self-modification, gateway integration, or remote telemetry. This is a generic reference extraction, not a full migration of a private deployment; the [scope matrix](docs/SCOPE.md) lists intentional omissions.

## Claims and limitations

An [exploratory BrowseComp study (2026-10-30)](docs/evaluations/2026-10-30-browsecomp.md) observed **a gain in favor of MAGI: 3/8 correct (37.5%), versus 2/8 (25.0%) with standard Hermes — one additional correct answer, or +12.5 percentage points**.

**That observed gain is a result of this test; its repeatability and generalizability remain to be confirmed.** The small sample does not establish a general quality advantage or equivalence, and MAGI used more tokens. This tests a specific deployment, not the standalone public package; its private execution environment is not reproduced by this repository. The report publishes calibration, per-run metrics, methods and limitations.

The [evaluation guide](docs/EVALUATION.md) separates recorded studies from proposed designs. A test suite passing proves only the behavior those tests cover.

A prompt cannot promise to eliminate hallucinations, enforce permissions, or remember between chats. The reference CLI does not run tools for the assistant. Do not replace real approvals, sandboxing, or secret management with this protocol.

## Development and release checks

```sh
python3 -m unittest discover -s tests -v
python3 tools/audit_release.py . --pretty
python3 tools/build_release.py --output ../magi-release.zip
```

`release-files.json` is the exact publication allowlist. The builder rejects unexpected source files (apart from documented local build/cache directories), symlinks, unsafe paths and an existing output. It produces a ZIP with normalized metadata and an internal SHA-256 manifest; `.git` is never included. Keep private audits and build outputs outside the repository. **A clean scanner result is not a guarantee that no personal information exists: manual review remains required.**

Optional packaging into a Python environment: `python3 -m pip install .` (inside a virtual environment). Installing is not necessary for the examples above.

## License and provenance

**MAGI — project initiated and directed by Lucas.**

The original code, protocol and documentation are licensed under the [Apache License 2.0](LICENSE). Anyone may use, modify and redistribute them, including commercially, subject to its terms. Preserve applicable notices; public access does not grant write access to the official repository. See [NOTICE](NOTICE), [provenance and platform attribution](NOTICE.md), and the optional [citation metadata](CITATION.cff). No third-party source code or model weights are vendored.

Automated GitHub Actions are not enabled in this initial distribution. A reviewed [CI example](docs/CI.md) is provided; local verification results are documented in [VERIFICATION.md](docs/VERIFICATION.md).
