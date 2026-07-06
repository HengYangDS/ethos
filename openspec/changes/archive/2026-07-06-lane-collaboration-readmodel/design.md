## Context

The official OpenSpec boundary is the promoted `ethos-repository` and
`ethos-adapters` specifications. The ETHOS product boundary is the Git-native
workspace status read model: worktrees, branch roles, Work Lane leases, claim
bindings, dirty state, path scope, and coordination state.

The symptom is agents invading one another's Work Lanes. The root cause is not
that assistant hosts lack a chat surface; it is that a foreign lane was visible
without an explicit product capability boundary. A lane is a Change container,
not just a branch. Observing a lane should help coordination; it must not imply
write, land, or retire authority.

## Design

Add a small, stable capability section to every `foreign_work_lanes[]` item:

- `current_actor_capability = "observe"`
- `allowed_actions = ["observe"]`
- `forbidden_actions = ["write", "land", "retire"]`
- `write_policy = "owner_only"`
- `retire_policy = "owner_handoff_or_maintainer_break_glass"`
- `handoff_required = true`

This keeps the collaboration mechanism under the existing kernel:

```text
Change = Work Lane
Commitment = lease + claim + path scope + role policy
Evidence = status JSON + proof + Git HEAD binding
Claim = lane claim binding
Chronicle = land, closeout, retire, or break-glass record
```

Communication starts as a repository read model: all agents can see which lanes
exist, who owns them, what scope signals exist, and what they are allowed to do.
Future host messages or handoff records can be projections or promoted evidence,
but the semantic center remains repository truth.

## Alternatives

- Add a host message bus first: rejected because it would make an assistant host or
  another provider surface look like the truth center before the repository
  capability boundary is explicit.
- Hide foreign lanes: rejected because hidden state is exactly what lets agents
  collide late.
- Make every foreign-lane conflict blocking: rejected because Git fast-forward
  and evidence-gated land already arbitrate mutation; the read model should show
  contention without serializing independent work.
- Allow maintainer cleanup by raw Git: rejected because head-bound, evidenced
  ETHOS commands are the product lifecycle.

## Proof Strategy

- Schema validation covers the new `foreign_work_lanes[]` fields.
- Unit tests cover workspace status and CLI contract payloads for foreign lanes.
- OpenSpec validation proves the promoted spec deltas remain valid.
- `ethos status --json`, `ethos report --json`, and executed proof bind the
  change to the Work Lane head before land.
