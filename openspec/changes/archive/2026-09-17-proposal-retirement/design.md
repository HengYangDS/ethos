## Context

Publication already owns independent peer preflight, immutable requests,
TransitionPlan execution, exact Git CAS, observations and Attestations. Its
nonzero-source equality invariant currently excludes deletion, while its
postcondition always expects the source object. Neither assumption describes
retiring an accepted review projection.

## Decisions

Extend the existing update model with deletion semantics represented by Git's
native zero OID, not a second transaction or a persistent retirement database.
The public publication command selects retirement explicitly; request replay
retains that choice through its exact desired refs. Reject mixed projection and
retirement in one request so their authority and proof claims remain distinct.

For retirement, the current accepted branch owns the policy. Read the local
accepted object, each peer's proposal and accepted branch, and the native Forge
open-review query. Require ancestry or an exact old-to-replacement mapping
revalidated by the existing completed history-repair owner, with that replacement
absorbed by accepted dev. Bare patch equivalence is not sufficient. A matching open
review blocks; unavailable, malformed or unrelated results are unknown. Native
provider credentials and endpoint resolution remain unchanged. Plain Git peers
have no Forge review only when their declared provider is Git; unsupported
providers cannot silently become review-free.

The existing peer declaration optionally names `forge_repository` when its API
repository URL differs from Git transport. Preserve the exact scheme and port;
SSH aliases and ports cannot supply API coordinates. This is connection metadata,
not a compatibility carrier or a second policy source. Credentials remain owned
by the native client. Git-only peers explicitly declare provider `git`.
Host-private connection metadata can use `remote.<name>.forgeRepository` in
local Git configuration instead of entering tracked product source. Explicit
peer declarations take precedence; missing SSH-to-API coordinates stay unknown.

Reobserve absorption, review and target identity at every peer effect, including
recovery. Git supplies exact-old deletion through an empty-source refspec and
atomic peer-local updates. Already absent refs are observed success, not a replay.
An uncertain transport result is followed by observation; unavailable outcomes
remain unknown. Forge review and Git refs are separate systems: no cross-system
atomicity, fencing of a concurrently reopened review, or global CAS is claimed.

## Boundaries

No new runtime dependency, custom Git transport, second admission parser, review
closure effect, remote protection mutation, adopter write, or compatibility
carrier. Unchanged publication consumers keep their source/proof semantics.
Native CLI authentication failures terminate with a precise next action; no
interactive login, unchanged retry or credential scope expansion is introduced.

## Verification

Start with failing exact-deletion contract and public CLI tests. Exercise local
bare peers and controlled native CLI outputs for closed/open/unavailable reviews,
protected refs, unequal proposal tips, SHA-1/SHA-256, partial publication and
replay. Assert actual remote refs and unchanged accepted/main objects. Reuse
existing signed fixtures and publication tests rather than cloning another
lifecycle harness. Finish native quality checks and exact lifecycle proof.
Native proof, archive, acceptance and runtime installation are effect-time
preconditions and receipts, not checkboxes whose update would invalidate the
source being proved. Task completion records the implementation and source
checks; the lifecycle independently proves and delivers those frozen bytes.
