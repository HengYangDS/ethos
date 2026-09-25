## Context

See [proposal.md](proposal.md). Completed repair and accepted-closeout
Attestations bind exact former commits, repository identity, effects and
replacement history. Publication rechecks those records. The current replay
path asks the general repository identity reader to parse each former commit's
entire profile under the latest schema; an unrelated retired field makes valid
old evidence unreadable.

## Goals and Non-Goals

- Keep repair and accepted-effect provenance verifiable after operational
  profile schemas evolve.
- Preserve exact historical identity, hashes, effect and replacement checks.
- Keep the live profile strict; do not add a legacy schema or adopter exception.
- Do not relax protected-ref, proof, tag or remote-CAS admission.

## Decisions

### Read only the historical identity during immutable effect replay

For each former commit, read `.ethos/profile.toml` from that exact Git tree and
parse TOML only far enough to require a nonempty string `profile_id`. Compare
`repository:<profile_id>` across the recorded effect's revisions and with the
repair coordinates. Do not substitute the current checkout's identity. The
existing repair checks still rederive the former policy and hash both that
policy and the original commit payload. A missing or malformed former profile
remains a hard failure.

An alternative is to make the general current-profile parser tolerate retired
fields. That would weaken present-tense configuration validation and retain
obsolete schema indefinitely. Another is to trust the recorded repository
string without rereading the old commit. That would lose the independent
historical identity binding. Both are rejected.

### Share the narrow reader only across completed repair checks

The existing repository-profile adapter owns one narrow reader for an exact
historical tree. Completed repair revalidation uses it for original
coordinates; the Git-effect validator uses it whenever it verifies an
immutable effect with current postconditions deliberately disabled. Current
effect admission still uses the strict typed parser. An effect without an
immutable plan cannot request historical identity resolution. This avoids two
historical parsers without making old fields valid in the current profile.

## Risks and Trade-offs

- A historical profile may be syntactically valid but contain old fields no
  longer understood. The narrow helper intentionally ignores those fields;
  signed repair evidence, exact old commit, hashes and effect validation still
  carry the other obligations.
- A tampered or ambiguous repair record must not reach the helper as an
  authorization shortcut. Existing record and effect checks remain in place;
  focused negatives cover mismatched identity and bindings.

## Migration Plan

Add an old-profile fixture with a retired field, reproduce the public selected
peer preview failure, then make focused repair and publication tests pass. Run
strict OpenSpec, static and full source proof. Accept through this Work Lane,
install the product runtime in the adopter, and rerun read-only peer-scoped
publication preview. Remote ref repair and release remain separate effects.
