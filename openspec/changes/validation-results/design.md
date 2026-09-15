## Context

See proposal.md for the failure boundary. The locked official CLI emits a full
`items` collection, individual Boolean `valid` values, severity-bearing issues
and summary counts. Its findings-only projection is a distinct report and is
not requested by ETHOS. Native process outcome and report meaning are separate
inputs; neither may erase a failure in the other.

## Decision

Keep translation in the existing lifecycle report reducer. Require the fields
whose meaning it consumes, reject malformed items and preserve native process
failure even when there is no item-level explanation. Evaluate invalid items
independently of exit status. Do not infer failure from the presence of an INFO
finding or duplicate the official validator's severity rules.

Public reports retain the original command, exit code and JSON for diagnosis.
Distinguishing tests cover failed empty results, malformed collections and items,
contradictory successful exit with invalid items, mixed severities, and valid
empty and informational results. At least one test reaches the existing public
CLI consumer; native successful reports are replayed without a second parser.

## Alternatives

- Only adding a nonzero-exit fallback leaves malformed successful reports and
  invalid-item contradictions undetected.
- Treating every issue as an error rejects official informational observations.
- A copied report schema or custom Markdown validator adds another authority.
  Validate only the native result boundary consumed here.

## Execution And Migration

1. Preserve the smallest owner and public-consumer RED cases.
2. Replace the reducer and correct incomplete synthetic producer fixtures.
3. Run affected consumer tests and native report replay, then bounded static
   prerequisites and exact proof through the existing lifecycle.
4. Install the accepted package before claiming adopter availability.

The existing quality skill will require checking selected gate dependency
closure and carrying the explicit resource envelope into each process. The
previous accidental preflight expanded `generated-artifacts` into the full test
suite; it was interrupted and is not acceptance evidence. This guidance does not
replace native gates, increase workers or introduce another execution store.

Hosted verification exposed a download-cleanup test whose readiness assertion
depended on both subprocesses starting within the timeout under test. Establish
the descendant through a loopback handshake before the unchanged timed wait;
require connection closure afterward. A delayed-start case must pass, while
terminating only the parent must fail. This corrects the test prerequisite, not
the production timeout or the required process-group cleanup.

Publication result state must preserve observed progress independently of the
verdict. If a completed peer precedes a failed observation, the execution owner
returns partial progress with an unknown verdict, applied and pending peers,
and the existing fresh-observation continuation. Before any peer is applied,
an unavailable preflight remains unperformed; an unobserved post-write outcome
remains unknown rather than confirmed applied. CLI and Attestation consume that
same result. Retry observes exact refs and recognizes completed peers instead of
repeating their pushes. No CLI-specific exception or additional state store is
needed.
