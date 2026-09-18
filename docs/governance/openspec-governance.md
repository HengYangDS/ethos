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
--json`, `ethos prove --full --json`, and `ethos land --json` consume the exact
current OpenSpec projection and compile its acceptance into a transient
Commitment.

For authoring, exact prewrite paths entirely inside one existing active Change
identify the intended Change without a separate selector. The official artifact
graph bounds incomplete-Change writes; ordinary Commitment attribution replaces
bootstrap after compilation succeeds. Public prewrite, pre-tool and native Git
commit consume the same current resolution and independently check authority.
A requested path does not grant permission or override an explicit selection.

Several active Changes do not justify guessing the owner of ordinary product
work. Without a selection, ETHOS directs the caller to the official Change list
and marks the choice as required. An invocation-local `ETHOS_CHANGE=<id>` selects
official intent across prewrite, pre-tool, native Git hooks, planning, proof and
source integration. An explicit command or API selection takes precedence.
The input identifies intent, never permission; exact source, Lease, runtime,
editor, policy and effect checks remain independent.

Use command-scoped environment assignment, for example
`ETHOS_CHANGE=<id> ethos lane prewrite <path> --json`. Removing that input restores
ordinary inference or ambiguity. Empty, invalid or missing selections fail
closed in an OpenSpec-enabled repository. No selector is stored in Git config,
Lease, a file or a database; repositories without this profile acquire no new
intent obligation.

Proof selection identifies the requested intent before comparing applicable
evidence. A carried exact Attestation ID selects that proof's intent instead of
an ambient environment choice; every current same-intent conflict and integrity
check still applies. One intent cannot borrow another intent's proof. A proof
selection is not effect authorization. Archive and multi-contribution lifecycle
completion remain separate acceptance obligations.

The archive write boundary is owned by a semantically namespaced Work Lane
command, not by a seventh root command:

```bash
ethos lane archive-change \
  --change <id> \
  --expect-head "$(git rev-parse HEAD)" \
  --apply --json
```

It invokes the pinned official OpenSpec executable, validates the exact archive
delta, commits through normal hooks, post-observes the exact Git effect, and
records a typed Attestation. A stale source or target ref, stale proof, foreign
holder, modified official output, repeated invocation, or reference drift is
blocked. Final proof recompiles acceptance from the exact official projection
at the resulting tree; archive bytes remain inert history.

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
