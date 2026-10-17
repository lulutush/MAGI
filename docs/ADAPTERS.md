# Adapters and safe trials

Each adapter includes the essential MAGI workflow and boundaries. None imports a private file, requires a plugin or hooks, changes model settings, or grants tool permissions. A text adapter can guide behavior; it does not enforce it. Start with synthetic inputs in a disposable context, not a production project or personal history.

## Common installation contract

From the repository root with Python 3.10 or later:

```text
python3 tools/install_adapter.py TARGET --destination PATH [--apply]
```

- `TARGET` is `hermes`, `claude-code`, or `gpt`.
- `PATH` must be explicit and name a **new, absent directory** under an existing parent you control, outside the source checkout. Do not target an existing installation or existing project.
- Source and destination paths must have no symlink components or `..` segments. The current installer requires POSIX no-follow/directory-descriptor support and refuses unsupported platforms rather than weakening checks.
- Without `--apply`, inspect the dry-run plan; nothing is installed.
- With `--apply`, only the selected directory is written. No host configuration is patched.
- The Hermes destination must be the skill directory named `magi`, **not** `HERMES_HOME` or its entire `skills` directory.
- Do not overwrite an existing adapter to update it. Review differences and obtain separate authorization for any replacement or merge.

Example staging sequence on a compatible POSIX host, using a new temporary parent outside the source checkout. Ensure the resulting parent path has no symlink components; otherwise choose an authorized, symlink-free parent explicitly:

```sh
TRIAL_PARENT="$(mktemp -d)"
python3 tools/install_adapter.py hermes --destination "$TRIAL_PARENT/magi"
python3 tools/install_adapter.py hermes --destination "$TRIAL_PARENT/magi" --apply
python3 tools/install_adapter.py claude-code --destination "$TRIAL_PARENT/claude-project"
python3 tools/install_adapter.py claude-code --destination "$TRIAL_PARENT/claude-project" --apply
python3 tools/install_adapter.py gpt --destination "$TRIAL_PARENT/gpt-text"
python3 tools/install_adapter.py gpt --destination "$TRIAL_PARENT/gpt-text" --apply
```

The expected files are `magi/SKILL.md`, `claude-project/CLAUDE.md`, and `gpt-text/INSTRUCTIONS.md` under that parent. `mktemp` creates the parent separately; the installer does not create missing ancestors. Staging is not host activation. Inspect the copied text before any live use. Keep trial output out of a public release unless it has been reviewed separately.

## Hermes

Source: [skills/magi/SKILL.md](../skills/magi/SKILL.md).

The adapter is an ordinary skill with standard YAML front matter, `name: magi`, and a description. Its content is self-contained and capped at 8,000 characters. It does not install a plugin, hook, memory backend, scheduler, or configuration change.

For actual use, choose the intended Hermes home/profile yourself. Its standard layout is `HERMES_HOME/skills/magi/SKILL.md`. After reviewing the staged file, rerun the installer with the explicit, previously absent skill-directory destination for that home. Do not infer which profile is intended and do not point the installer at `HERMES_HOME` itself. The parent directory must be one you have authorized.

Once the host can discover the installed skill, load it in an interactive session:

```text
/skill magi
```

Run the synthetic trial below. Confirm the skill is available using the host's supported interface; seeing a file on disk alone is not proof that it was loaded. Discovery or refresh behavior may depend on the host version. This guide does not claim a live Hermes integration test has been performed.

## Claude Code

Source: [adapters/claude-code/CLAUDE.md](../adapters/claude-code/CLAUDE.md).

The adapter is a self-contained project `CLAUDE.md` under 150 lines. Use the installer to create a new disposable project directory, then open that directory in Claude Code and start a fresh session with the synthetic trial. Do not replace an existing project's `CLAUDE.md`, merge into global instructions automatically, or add imports to private files.

Claude Code documentation describes `CLAUDE.md` as contextual instructions rather than hard enforcement. Follow the host's hierarchy, sandbox, and approvals; MAGI cannot change them. Record other loaded guidance during a test because it can affect results, but do not copy private instructions into a public report. This guide does not claim a live Claude Code integration test has been performed.

## GPT or an instruction-capable chat

Source: [adapters/gpt/INSTRUCTIONS.md](../adapters/gpt/INSTRUCTIONS.md).

The adapter is standalone instruction text of fewer than 8,000 characters. Review it, then place it in an instruction surface that your current host supports. Where persistent custom instructions are unavailable, supply it as ordinary user-level guidance for a disposable conversation; its authority remains that assigned by the host. Staging the file locally does not upload it or configure a GPT.

Use only the capabilities actually available in that chat. Browsing, shell execution, file tools, delegation, and memory are **not** assumed. Without a real execution tool, CLI commands are instructions for the user, not completed work. Do not promise permanent inter-chat memory or automatic state synchronization. No external action, API key, connector, or knowledge upload is required for the synthetic trial.

This is a generic setup guide, not an attestation of the current GPT editor UI. The relevant OpenAI help page could not be inspected during preparation because of an access challenge/HTTP 403; no current UI path, product entitlement, or live GPT test is asserted.

## One synthetic smoke test for all hosts

Start a clean trial, avoid connecting personal stores, and provide:

> Use MAGI. Draft a reusable summary from this synthetic input: title = Test note. A source document and review date are required but were not supplied. Do not access files, history, memory, or external tools.

Expected observations, not reported test results:

- A draft or explicitly partial answer, not a completed factual summary.
- The source document and review date are identified as missing.
- No invented source, date, history, tool result, or persistent write.
- A concise result; no unnecessary delegation or lengthy ritual.
- If a durable envelope is used, it follows the compact profile: `meta`, `content.payload`, text-only `language`, and the eight QA lists. Record the source document and review date in `qa.required_inputs` and `qa.missing_inputs`, with questions in `qa.user_questions`; do not put COMP lists in `content`.

Then ask for the same task with "MAGI off". Honesty, safety, privacy, and ordinary host requirements still apply. This comparison is a smoke test, not proof of a quality difference. The [evaluation plan](EVALUATION.md) describes a controlled comparison.

## Local helper checks are separate

The adapters and blank templates use the [compact artifact profile, not full governance](ARTIFACT-PROFILES.md). `meta` requires nonempty `artifact_id`, `artifact_type`, and `version`, plus `status` (`draft`, `provisional`, or `validated`). `qa` requires list fields `checks`, `assumptions`, `limitations`, `warnings`, `required_inputs`, `provided_inputs`, `missing_inputs`, and `user_questions`. Checks are objects with `name`/`status` and optional `reference`/`note`; the other lists contain strings. The gate's separate evidence file is not an artifact QA field. Repository documentation links in adapters are optional references, not imports or dependencies needed after standalone installation.

These commands run locally only when an actual terminal is available; they do not invoke any of the three hosted assistants:

```sh
python3 -m magi route 'Draft a synthetic checklist without external actions.' --pretty
python3 -m magi gate 'Draft a synthetic checklist without external actions.' --evidence examples/evidence.json --pretty
python3 -m magi validate examples/artifact.json --pretty
```

Read real output before making claims. `checklist_satisfied` is a declaration-level gate outcome, not independent verification. Structural validation cannot prove source authenticity or semantic correctness. Do not present this page's examples or expected observations as executed results.

## Reference and verification scope

- [Hermes skills documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/): source for the `SKILL.md` layout and `/skill magi` convention.
- [Claude Code memory and CLAUDE.md documentation](https://code.claude.com/docs/en/memory): source for project-context instructions and their limits.
- [OpenAI: Creating a GPT](https://help.openai.com/en/articles/8554397-creating-a-gpt): reference pointer only; inaccessible during preparation, so no current interface claims rely on it.

Host documentation can change. Verify the relevant public documentation before a real installation. See also [privacy boundaries](PRIVACY.md) and the [common protocol](../protocol/MAGI.md).
