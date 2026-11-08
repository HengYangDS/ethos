# Proposal

## Why

`peer-identity-redaction` lets adopters remove a protected peer's identity from their tracked
records, but nothing stops a new literal from reaching a peer: the content scans judge only
private-class addresses, and a forge's own host may be public-class or opted in. The archived
`rc-plan` (Appendix F) settles a push-time check over what a push adds beyond every tip the peer
advertises, a backstop for raw pushes, a mode each adopter turns on once its tree is clean, and a
keyless verifier that admits only marker edits that reproduce what they replace.

## What Changes

- `peer_identity.mode` in the repository profile, `disabled` by default or `required`, read at the
  commit whose policy push admission already trusts; a protected peer under `disabled` and an unread
  mode are `status` advisories; the redaction preview counts the literals outside the record roots.
- The push-time check in `push_admission_report`: the commits
  `<pushed> --not <every advertised tip>` and a pushed tag's message refuse a fed host, a fed full
  path, `:<port>` after any host and a closed context with a fed value, as
  `peer_identity_literal:<form>:<n>:<m>:<line>`, which never repeats a value; an unreadable
  advertisement is `unknown` and refuses under `required` with
  `peer_identity_range_unknown:<remote>`. The publication request path reads the remote-tracking
  refs instead of the network.
- `hook commit-range --check peer-identity`: the backstop for raw pushes, fed from the GitLab job's
  variables, inert without them, exiting 1 only on a fed literal under `required`; a missing base is
  the advisory `peer_identity_backstop_baseline_missing`. The GitLab projection runs it after the
  policy step of the same job.
- The keyless verifier in commit validation: a changed line under a record root that introduces a
  marker pairs with the removed line it reproduces; `record_marker_unpaired`,
  `record_marker_malformed`, `record_marker_unkeyed` and `record_roots_unread` refuse.
- wib's `[artifacts]` table retires through a repair to `record_roots = ["evidence/"]`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: the private-class address requirement's scans read what a push adds beyond
  every advertised tip; the keyless verifier is added.
- `repository-governance`: the push-time check, the backstop, the profile mode and the `status`
  advisories.

## Impact

- New `src/ethos/adapters/admission/peer_identity_push.py` (the push check and its readers),
  `src/ethos/application/peer_identity.py` (the backstop and the `status` advisories),
  `src/ethos/adapters/repo/commit/record_markers.py` and `src/ethos/repository/paradigm/records.py`;
  `peer_identity.py` gains the keyless alignment, `peer_feed.py` the CI feed and `profile.py` the
  mode.
- `src/ethos/adapters/admission/publication.py`,
  `src/ethos/application/publication/request_gaps.py`,
  `src/ethos/adapters/repo/commit/integration.py`, `src/ethos/adapters/repo/invocation_facts.py`,
  `src/ethos/surface/cli/hook/commands.py`, `src/ethos/application/inspection.py`,
  `src/ethos/repository/paradigm/report.py` and `src/ethos/repository/paradigm/repair.py` (the
  record binding), `.config/ci/pipeline.cue` and the `.gitlab-ci.yml` it generates, the
  projection tests, and `docs/reference/operational-roots.md` (turning the check on).
- Tests: the push check, the backstop and the status advisories; the keyless verifier and the marker
  alignment; the record binding's two repairs and its refusals.
- Each adopter's job goes through its own CI declaration owner in its activation lane.
