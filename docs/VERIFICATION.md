# Verification of this source distribution

This report concerns the generic source distribution, **not** a live assistant deployment or a model-quality benchmark. Private review inputs, raw reports, paths and identities are not distributed.

## Observed local results

- **116 automated tests passed** using CPython 3.13.14 on a POSIX host.
- Coverage includes the router, declared-evidence gate, compact and fuller governance validators, malformed/deep/oversized JSON, documentation examples, empty memory/registry templates, relative links, packaging guards and adapter-copy installation into temporary directories.
- Installer checks include simulation-only defaults, non-overwrite, symlink refusal, explicit destination, read-back checks and failure cleanup. No live profile was installed into.
- The generic release-tree audit returned no findings.
- A separate private known-identifier check returned no findings after narrowly scoped, exact-line exceptions for the expressly chosen public project credit and public repository URL. Its inputs and reports are not included.
- A Gitleaks 8.30.1 working-tree scan returned no findings. Publication also requires a separate history scan; tree scanning does not inspect history.
- A wheel was built without network dependency resolution and installed into a fresh virtual environment. Import resolved to that environment's installed package, and the CLI was exercised there. The wheel contains the Apache-2.0 SPDX metadata, LICENSE and NOTICE.
- The Apache license file was checked against the official Apache Software Foundation text. Citation metadata was validated against the Citation File Format schema.
- Python sources passed a Python 3.10 syntax check. Actual local runtime execution used 3.13.14.
- A packaging regression test covers the inclusion of NOTICE and CITATION.cff. The scanner's phone-shaped test input is deliberately invalid and all-zero rather than a plausible personal number.

## Scope of these results

These are executable correctness and packaging checks, not proof of universal absence of sensitive information, permission bypass resistance, factual truth, model compliance or improved answer quality. Review is still required when files change.

- Hermes skill discovery in a live user profile was not exercised.
- Claude Code model behavior and inherited live project instructions were not exercised.
- No GPT was created, published or tested through a live account.
- No API/model credentials were used by the tests.
- No Python package was uploaded to a package registry.
- GitHub Actions is not activated in this distribution. The [optional CI example](CI.md) and its intended version matrix are not evidence of a completed hosted run.

## Reproduce

From the source directory:

```sh
python3 -B -m unittest discover -s tests -v
python3 -B tools/audit_release.py . --pretty
python3 -B governance/validate.py governance/example.json
python3 -B -m magi validate examples/artifact.json
```

The project's archive builder includes a generated `MANIFEST.json` with per-file SHA-256 hashes. It excludes Git metadata and local build/test caches. `release-files.json` lists allowed source files, and `tools/build_release.py` rejects unexpected files and validates a generated manifest when rebuilding an extracted archive. GitHub's own source downloads are separate archives and do not automatically add this generated manifest.

Before each external release, rerun checks on the final bytes, review the selected Git history and public identity, preserve the license/notices and explicitly approve the destination. See [the publication checklist](PUBLICATION.md).
