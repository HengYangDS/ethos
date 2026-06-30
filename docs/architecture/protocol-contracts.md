---
subject: ethos:protocol-contracts
role: reference
state: canonical
relations:
  canonical_for: ecosystem compatibility
---

# Protocol Contracts

ETHOS protocols are language-neutral before they are Python APIs.

The native protocol set is JSON Schema for command output and kernel objects,
SQLite for ignored local runtime state, JSONL for append-only event exports, and
TOML for human-authored project configuration.

External standards enter by adapter contract. SLSA-style provenance,
Sigstore-compatible signing, OpenTelemetry semantic conventions, CUE, OPA,
Dagger, Temporal, and MCP may extend execution or projection, but they do not
replace the kernel.
