---
subject: ethos:openspec-repository-governance
role: policy
state: canonical
relations:
  canonical_for: spec-driven repository governance
---

# OpenSpec Governance

Status: canonical.

Purpose: define the boundary between official OpenSpec lifecycle ownership and
ETHOS lifecycle consumption.

See also: [Command Plane](../reference/command-plane.md) and
[Terminal Governance Product Design](../plans/terminal-governance-product-design.md).

OpenSpec is the official repository carrier for change proposals, deltas,
validation, and archive operations. The official CLI owns that lifecycle:

```bash
openspec list --json
openspec status --change <id> --json
openspec validate --all --strict --json
openspec archive <id> --yes --json
```

ETHOS does not reproduce those operations as public roots. `ethos plan --changed
--json`, `ethos prove --full --json`, and `ethos land --json` consume the current
OpenSpec facts when the selected Commitment requires them.

The archive write boundary is owned by a semantically namespaced Work Lane
command, not by a seventh root command:

```bash
ethos lane archive-change \
  --change <id> \
  --expect-head "$(git rev-parse HEAD)" \
  --apply --json
```

It invokes the pinned official OpenSpec executable, validates the exact archive
delta, commits through normal hooks, relocates the current Lease to the archived
Commitment, and records a typed Attestation. A stale HEAD/tree or proof, foreign
holder, modified official output, repeated invocation, or reference drift is
blocked. The archived Commitment remains only the exact intent binding for final
proof and land; it does not become current specification authority.

An OpenSpec archive is valid only when the official command completes its
required validation and updates the accepted specification surface. ETHOS
records no parallel lifecycle log and does not infer archive success from a
folder name or a prior command output.

Archive follows absorption. Before a Change is archived, its accepted semantics
must be integrated into the owner-native specification surface and any durable
architectural ruling must be represented by the canonical document or decision
record that owns it. The archived Change then preserves change history; it does
not remain a second source of current instructions.

If a proposed delta conflicts with current specifications and both meanings are
valid, the conflict is a model gap. The Change must first raise the affected
taxonomy, ontology, contract, or boundary so both cases are represented without
ambiguity. Forcing the new case into an unsuitable category, silently dropping
one side, or archiving before that integration is complete is invalid.
