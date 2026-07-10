---
subject: ethos:local-state
role: explanation
state: canonical
relations:
  canonical_for: ignored runtime state
---

# Local State

ETHOS stores host-local runtime state in `.ethos/state/state.sqlite`. The
directory is ignored except for `.ethos/state/.gitignore`. Tool runtime caches
live under ignored `build/runtime/tool-cache/`, not under `.config/`, because
configuration policy and runtime working state are different subjects.

SQLite records coordination and replay aids. It does not pre-create
speculative cache stores; action cache keys stay in action-graph contracts
until a concrete runtime cache earns its own owner and lifecycle.

- `schema_migrations`
- `events`
- `sessions`
- `leases`
- `gate_runs`
- `action_runs`
- `evidence_index`

Chronicle events may also be stored locally for fast inspection. Durable truth
remains repository files, schemas, claims, and evidence records. Local state can
be deleted and rebuilt without changing repository history.

Work Lane leases are local coordination facts recorded by lane-start flows. They
support ownership, handoff, and closeout ordering checks, but they do not replace
Git history, OpenSpec records, claims, evidence, or Chronicle judgments.
Productized leases identify the concrete acting holder, not merely a provider
class; older owner strings remain compatibility fields until the runtime schema
fully exposes `holder_ref`, epoch, heartbeat, and Authority-policy capability.
Current prewrite and apply-mode admission are enforced by checkout role,
editor-root binding, HEAD checks, and active lease holder binding where the
command surface supports it.

## Adopted Repository Control Roots

When external ETHOS inspects an adopted repository from a linked Work Lane, the
accepted-root checkout remains the local coordination control root. ETHOS may
read the adopter's ignored `.cache/local-state/worktree/leases.json` projection
from that accepted root to preserve existing embedded Work Lane leases during
shadow parity and rollback-window checks. This compatibility read is local
runtime coordination only: it does not promote `.cache/local-state/` to durable
truth, does not replace `.ethos/profile.toml`, and does not let product code own
adopter-specific profiles or fixtures.

SQLite `.ethos/state/state.sqlite` remains the product-native local-state store;
when both SQLite and JSON projections contain the same branch, the SQLite lease
wins. Expired or malformed JSON projection leases are ignored. The JSON
projection exists so external ETHOS can be at least as strong as an adopter's
embedded backend while the adopter is still in migration.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
