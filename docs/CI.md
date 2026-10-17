# Optional continuous integration

This initial public source distribution does **not** enable GitHub Actions. Continuous integration is an optional, explicit maintainer step rather than an automatic side effect of using MAGI. The project tests were run locally, as documented in [VERIFICATION.md](VERIFICATION.md).

The reviewed configuration is provided as [ci/check.yml](ci/check.yml), outside the active workflow directory. Its Python matrix describes intended checks, not completed hosted runs.

A repository maintainer may enable it later using their own authorized GitHub workflow access:

1. Review the referenced actions and their pinned commit hashes.
2. Move `docs/ci/check.yml` to `.github/workflows/check.yml`.
3. Replace that path in `release-files.json`, keeping the allowlist synchronized.
4. Run the local tests, audit and archive builder again.
5. Commit the change, then verify an actual successful Actions run before claiming CI is passing.

The example requests only `contents: read`, does not persist checkout credentials and does not require project secrets. Do not introduce write tokens or secret-dependent execution for untrusted pull requests.
