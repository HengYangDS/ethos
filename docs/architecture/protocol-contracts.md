---
subject: ethos:protocol-contracts
role: explanation
state: canonical
relations:
  canonical_for: ecosystem compatibility
---

# Protocol Contracts

ETHOS protocols are language-neutral before they are Python APIs.

The native protocol set is JSON Schema for command output and kernel objects,
SQLite for ignored local runtime state, JSONL for append-only event exports, and
TOML for human-authored project configuration.

External standards enter by adapter contract. SLSA-style provenance, in-toto
statement envelopes, Sigstore-compatible signing, SPDX-compatible artifact
metadata, CDEvents-compatible event exchange, OpenTelemetry semantic
conventions, CUE, OPA, Dagger, Temporal, and MCP may extend execution or
projection, but they do not replace the kernel.

Adoption order:

```text
kernel schema -> command JSON -> local state -> adapter projection
```

If an adapter is unavailable, ETHOS keeps the same command JSON, local SQLite
state, and repository evidence semantics. This makes external frameworks useful
without making them mandatory.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
