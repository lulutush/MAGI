# Publication and release checklist

MAGI is an experimental public source distribution under the [Apache License 2.0](../LICENSE). The original project credit is recorded in [NOTICE](../NOTICE). Public availability permits reuse under that license, including commercial use; it does not give visitors write or merge permissions on the official repository.

Preparing a future release does not itself authorize uploading it, publishing a package, changing a license or enabling a public GPT. Those remain maintainer decisions.

## Before each release

- [ ] Approve the exact file set, documentation and destination.
- [ ] Preserve the license and applicable attribution notices; check rights to any newly added material.
- [ ] Remember that a public publishing account and its associations can identify the responsible party even when source files contain no private data.
- [ ] Inspect Git author/committer identities, dates, signing identity, messages, references and history. Never push a private deployment repository or copied private history.
- [ ] Keep write/merge access limited; review appropriate branch protections and private vulnerability reporting. Public forks remain possible.
- [ ] Review CI permissions before enabling or changing workflows. The initial distribution includes an [inactive example](CI.md), not a completed GitHub Actions run.
- [ ] Confirm actual host compatibility before claiming live adapter support.
- [ ] Rerun tests, targeted identifier checks, secret scans and archive verification on the final bytes.
- [ ] Explicitly approve the external publication step.

## Release manifest

`release-files.json` enumerates the exact source files allowed in the source ZIP. `tools/build_release.py` checks that list, rejects unexpected files, runs the generic release audit and writes only an explicitly requested new ZIP outside the repository. It excludes `.git`, caches, local trial directories, environments and build outputs; rejects symlinks and unsupported file types; normalizes archive timestamps and permissions; and creates `MANIFEST.json` with per-file size and SHA-256.

The generated integrity manifest contains no absolute local paths, user IDs, account names, build-host details or authors' emails. Hashes establish integrity, not trustworthiness.

Do not store unredacted scan output, private denylists, environment captures, model transcripts or shell history in this repository. No old benchmark artifacts are republished. [EVALUATION.md](EVALUATION.md) describes a prospective methodology instead.

## Evidence boundaries

Consult [VERIFICATION.md](VERIFICATION.md). Unit and isolated adapter tests do not establish that an LLM follows instructions, that a live integration was exercised, or that answer quality improved. A workflow example or declared version matrix is not evidence of a completed hosted CI run.
