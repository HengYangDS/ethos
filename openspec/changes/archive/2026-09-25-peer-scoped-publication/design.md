## Context

See [proposal.md](proposal.md). The existing publication effect already models
peer-local targets and exact-CAS updates; only request construction insists on
observing every declared peer. The application receives the complete peer map
from the validated repository topology. A receipt stores the compiled effect,
not the command-line spelling that created it. The executor rechecks source,
proof and ref obligations before the first effect and again per peer.

## Goals and Non-Goals

- Allow a caller to choose declared peers without editing tracked topology or
  obtaining an implicit fallback decision from network failure.
- Keep one publication effect model, immutable request store, executor and
  Attestation format. Preserve the current all-peer default.
- Make partial scope unmistakable in machine and human results, including
  continuations after an unavailable selected peer.
- Preserve full topology validation, current source and proof, ref roles,
  exact remote OIDs and selected peer identity across receipt replay.
- Do not introduce a second publication command, ambient selection variable,
  credential path, automatic retry of authentication failures, or a claim that
  publishing one peer publishes every declared peer.

## Decisions

### Select at the application boundary; bind through the existing effect

Add a repeatable `--peer` option to the public `publish` command and pass its
IDs to the existing application operation. After observing the complete
declared topology, reject duplicate or unknown IDs. A new request filters the
declared peer map in declaration order before exact remote observation. No
selector retains the current complete map. The existing `PublicationEffect`
targets and content-addressed request thereby carry the selected set without
a new field or store. A selector with `--receipt` is invalid: replay consumes
exactly the bound targets, not a caller's new choice.

### Recheck identity as well as remote name

The current push admission verifies that a Git remote remains declared, but
that alone does not protect a receipt whose peer ID is relabeled. Before and
between effects, compare every target's `(id, remote)` with the freshly
validated full topology. A missing or remapped selected ID blocks all further
effects. The existing proof, signature, ref-policy and exact-CAS checks remain
unchanged and run for each selected target. The unselected peers are never
read by the exact request observer or written by the executor.

### Report scope without promoting it to global success

Keep `published` as the terminal state of the *requested* effect, whose
Attestation already binds its target set. Correct the existing
`declared_peer_count` to mean the full topology, and add explicit selected and
unselected peer IDs to the result. A failed re-probe continuation retains
`--peer` so it cannot silently widen back to all peers. The local readiness
view remains a separate all-topology observation and claims no remote push.

## Risks and Trade-offs

- An operator can choose to publish only one peer even while others are
  healthy. This is an explicit bounded choice, not an automatic outage policy;
  results must make the unsent peers visible.
- A selected peer can itself become unavailable after request creation. The
  existing unknown/partial-effect path remains authoritative and never
  substitutes another peer.
- Existing all-peer receipts remain valid. New subset receipts use the same
  typed effect and are rejected if their selected ID-to-remote binding or
  other current admission changes.

## Migration Plan

Exercise a two-peer native fixture with one unreachable peer, including the
default all-peer refusal, selected-peer preview, receipt replay, negative
selectors, altered peer binding and accepted/release proof paths. Run strict
OpenSpec, focused publication suites and the full source proof. Accept and
install through the owned Work Lane, then exercise the installed command on
an adopter's declared dual-peer topology before any real remote effect. Remote
branch repair, protection and hosted release remain separately admitted.
