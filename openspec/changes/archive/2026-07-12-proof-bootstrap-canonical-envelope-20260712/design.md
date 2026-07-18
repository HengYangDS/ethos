## Context

Control-path closeout deliberately requires an incumbent or protected external
bootstrap verifier so a candidate cannot approve its own governance controls.
The verifier already checks exact heads, control-tree digests, its own digest,
and a bootstrap decision. Its candidate-proof parser, however, was written
against a minimal test fixture rather than the public `ethos prove` result
contract. Native executed proof records carry their HEAD under
`data.evidence.head` and repeat it in `data.provenance.predicate.head`.

## Goals / Non-Goals

**Goals:**

- Bind the standalone control-replacement verifier to the native executed
  `ethos prove --execute --json` envelope.
- Require command identity, executed proof state, evidence binding, and
  provenance binding to agree on the candidate HEAD.
- Remove the bare top-level `{head, state}` proof-envelope format.

**Non-Goals:**

- Adding any adopter profile, provider adapter, agent account, credential,
  network service, daemon, or scheduler requirement.
- Changing branch-role semantics, the proof lattice, or the optional/default-off
  independent-verification policy.
- Editing, landing, retiring, or cleaning foreign Work Lanes.

## Decisions

### Consume the native proof result rather than duplicate its HEAD

The verifier accepts a candidate proof only when `command` is `prove`, `ok` is
true, `state` is `proven`, `data.executed` is true, and the candidate HEAD agrees
between `data.evidence.head` and `data.provenance.predicate.head`. This uses the
product's existing evidence and provenance envelope instead of inventing a
second convenience binding.

### Reject bare proof-shaped records

A record containing only `{head, state}` is not the public proof command result.
Rejecting it prevents a handwritten envelope from standing in for executed proof
and preserves a single native proof contract.

### Keep the control boundary generic

The verifier remains Python-standard-library-only and external to the candidate
worktree. It still hashes the complete proof file into the receipt and requires
an external exact-head bootstrap decision. The parser mentions no adopter or
provider term because closeout is product semantics shared by every profile.

## Risks / Trade-offs

- [Future proof-result shape drift] → The focused test is deliberately shaped
  like the public result; a deliberate public-contract change must update this
  verifier atomically.
- [Overclaiming local bootstrap] → The receipt remains local and
  non-authoritative; it does not imply hosted enforcement, remote publication,
  or an independent security boundary.
- [Compatibility pressure] → The old hand-authored envelope is intentionally
  not retained; rollback restores a prior atomic product revision rather than a
  permanent second format.

## Migration Plan

1. Replace the test fixture with a native executed proof result; it fails under
   the former top-level-head parser.
2. Require all native envelope bindings in the external verifier.
3. Validate focused admission tests, OpenSpec lifecycle, changed-path plan,
   executed proof, parity evidence, candidate land, accepted closeout, and
   local-only publication readiness.
4. If the public proof contract ever changes, revert this atomic change and
   repair the parser in a new governed Work Lane; do not revive a bare envelope.

## Open Questions

None. The observed executed proof result and existing public JSON contract
supply the required fields.
