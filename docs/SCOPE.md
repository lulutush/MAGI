# Release scope: what is portable and what is deliberately absent

This release is a **generic reference extraction**, not a byte-for-byte copy or full migration of a private running assistant. It preserves the method and offers small executable helpers. A fresh repository and curated files avoid carrying deployment history.

| Layer | Included | Deliberately not included |
| --- | --- | --- |
| Adaptive workflow | Full protocol and self-contained adapters; bounded EN/FR advisory router | Automatic interception of every host message; native model-setting changes |
| Evidence discipline | Explicit declarative gate and source/authority boundaries | Source authentication or automatic factual verification |
| Durable artifacts | Compact envelope validator, fuller governance profile and examples | Private artifact database, historical snapshots, domain catalogs |
| Stable memory | Selection/retention principles and an empty template | Personal memories, automatic collection, installed host-memory backend |
| Project context | Empty registry template and source-first rules | Project names, operational registries, private routes or endpoints |
| Retrieval | Optional semantic-retrieval architecture and trust limits | Vector database, embedding model, service credentials, index contents |
| Skills and delegation | Selection, scoping, verification and explicit approval rules | Private skill library, autonomous jobs, external agent launchers |
| Improvement | Observed → proposed → tested-and-approved method | Background self-modification, automatic rule promotion |
| Host integration | Native instruction files and explicit safe-copy installer | Plugins, hooks, patched host code, credentials, live-profile changes |
| Evaluation | Synthetic examples, executable mechanical tests, controlled-study plan | Personal feedback transcripts or a claimed model-quality benchmark |

This smaller scope is intentional. It lets a new user try the reliability method without needing another person's infrastructure or data. A later connector must be separately designed, permissioned, documented and tested; it must not be implied by an empty template.

The compact and full governance artifacts use distinct schemas. See [artifact profiles](ARTIFACT-PROFILES.md); successful validation of either establishes declared structural consistency only.
