# Artifact profiles

The small public CLI envelope and the fuller governance envelope are **different profiles**. Do not silently treat them as interchangeable.

## Portable compact profile

`python3 -m magi validate examples/artifact.json --pretty` checks the compact envelope used by the standalone adapters: `meta`, `content`, `language`, `qa`, with required/provided/missing input names in `qa`. This is a small onboarding format, not a claim of full MAG-STRUCT/MAG-COMP compatibility.

## Full governance profile

`python3 governance/validate.py governance/example.json` checks the declared structural rules of a fuller **MAG-STRUCT-1.0 + MAG-COMP-1.1** envelope. The example is synthetic and deliberately provisional.

- `meta`: technical identity, scope, version, timestamps, status, structured provenance, and standard identifier.
- `content`: machine-usable facts, calculations, rules, payload and dependencies.
- `language`: human-facing title, summary and explanation; not a substitute for machine truth.
- `qa`: checks, assumptions, limitations, warnings, required/provided/missing inputs and questions.

Root block order is `meta`, `content`, `language`, `qa`. Keys use ASCII snake_case. Required and missing inputs have `name`, `severity` and `reason`; severities are `blocking`, `important`, `nice_to_have`. Provided inputs use matching names. Missing inputs must exactly reconcile with required minus provided.

`draft` and `provisional` allow useful incomplete artifacts. A declaration of `validated` requires passing declared checks, and either no blocking/important missing inputs or a separate, explicit acceptance record for each such missing input. Acceptance records contain `name`, `accepted_by`, `acceptance_timestamp`, `acceptance_note`, and `impact`. Use a role or approved pseudonym when identifying an approver; never insert personal details unnecessarily.

Outstanding blocking/important inputs require recorded questions. Optional gaps remain disclosed. `deprecated` and `superseded` retain historical artifacts without recommending them for new use.

The validator checks shape, completeness arithmetic, status consistency and acceptance metadata. **It cannot authenticate an approver, discover every domain prerequisite, verify facts, confirm that a check was performed, or authorize a real action.** An acceptance record is not a security credential. Host permissions and separate human validation remain necessary. No domain requirement catalog, artifact database, semantic index or legacy-state migration is bundled.

Choose the compact profile for a small handoff; choose the fuller profile when provenance, missing-input severity and explicit exceptions matter. Ordinary answers need neither.
