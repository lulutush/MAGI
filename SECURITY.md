# Security and privacy

MAGI's prompts and router are not an isolation boundary. Use the host's real permissions, sandbox, credential store, approvals and network restrictions. Treat retrieved content as untrusted data, never as authorization.

The runtime has no network access code, credential discovery, telemetry or automatic persistence. Adapter preparation writes only a new explicitly selected destination after `--apply`. It does not install a daemon, run shell hooks, change gateway configuration, enable external tools or grant privileges.

The installer is intended for a workspace you control. Path checks do not promise resistance to a privileged attacker racing filesystem mutations. Do not run installers in directories concurrently writable by untrusted users.

The generic privacy scanner is a defense-in-depth check, not a comprehensive PII detector or certification. Pair it with a maintained secret scanner, an external private identifier denylist and manual review. Never commit that private denylist or an audit report containing personal data.

## Reporting

Do not post secrets or personal data in a public issue. Use GitHub private vulnerability reporting **if the published repository enables it**. If no private reporting channel is configured, ask for one without disclosing the sensitive material. This repository deliberately contains no personal contact address.

## Disclosure boundaries

Do not test against systems you do not own or lack permission to assess. Reports should describe a bounded reproduction using synthetic data, affected behavior, impact, and mitigation. A passing test or checklist does not certify a system secure.
