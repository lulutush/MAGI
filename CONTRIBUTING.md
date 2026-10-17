# Contributions and official versions

Issues and pull requests are welcome. Original contributions submitted for inclusion are offered under the project's Apache License 2.0 unless explicitly stated otherwise and accepted by the maintainer.

The maintainer retains control of the official repository. A pull request is a proposal, not permission to change the official code. Never enable automatic execution of untrusted contributions with write credentials.

Use fictional examples and reserved domains. Do not include private memories, transcripts, tokens, contact details, host configuration, personal attribution without permission, or production dumps in commits, issues, tests, screenshots or PRs. Repository history matters as much as the current tree.

Run `python3 -m unittest discover -s tests -v` and `python3 tools/audit_release.py . --pretty`. Add every intentional public file explicitly to `release-files.json`; release builds reject unlisted files. Preserve truthful separation between implemented behavior, planned integrations, deterministic checks and model-quality evidence.

Changes to permissions, persistence, network behavior, installers or privacy boundaries require explicit human review. Do not turn a remembered preference or a model output into operational authority.
