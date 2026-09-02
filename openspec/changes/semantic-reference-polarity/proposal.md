## Why

After an official Change is archived, its requirements become canonical OpenSpec
specifications. Repository semantic closure currently treats every path-shaped
literal in those specifications as a live consumer, so a requirement that says
a retired path SHALL be absent makes that same deletion fail post-archive proof.

## What Changes

- Define a path consumer by executable or navigable syntax, not by an arbitrary
  prose mention of a path.
- Apply the same Markdown-link boundary to canonical OpenSpec specifications as
  to other Markdown carriers.
- Retain exact detection for real code, configuration, import, command, and
  Markdown-link consumers of retired paths.
- Delete the test contract that promoted OpenSpec prose into a runtime consumer;
  OpenSpec owns required behavior, while proof and implementation tests establish
  conformance.
- Do not add polarity keywords, a negative-reference registry, a compatibility
  exception, or another persisted semantic carrier.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: define the semantic boundary between normative
  OpenSpec prose and an actual path consumer.

## Impact

Repository semantic-reference closure and its focused tests change. OpenSpec,
Commitment, Lease, Attestation, Git effects, and adopter layouts do not gain a
new entity or state.
