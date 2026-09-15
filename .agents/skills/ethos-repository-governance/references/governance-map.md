# Governance Map

Use this reference to choose the current owner without creating a second
command plane.

| Concern | Current owner | Evidence |
| --- | --- | --- |
| Repository facts and authority | `ethos status --json` | Current command JSON |
| Changed-scope gates | `ethos plan --changed --json` | TransitionPlan and required gaps |
| Local proof readiness | `ethos prove --json` | Current proof result |
| Focused capability proof | `ethos prove --execute --gate <gate-id> --json` | Executed gate result |
| Full local proof | `ethos prove --execute --full --expect-head <exact-head> --json` | Current object-bound proof result |
| Work Lane write admission | `ethos lane prewrite ... --json` | Current lane decision |
| OpenSpec intent and transformation | official `openspec` CLI | Official command JSON |
| Governed archive effect | `ethos lane archive-change --change <id> --expect-head <source-head> --json` | Exact source proof and the returned guarded continuation |
| Detached CI ref observation | `ethos hook ref-update --target-ref <full-ref> --proposed-head <oid> --remote-head <old-oid> --remote <name> --json` | Shared role, introduced-range and intent observation; not repository proof |
| Historical attribution/signature correction | `ethos lane repair-signature --root <accepted-root> --expect-head <old-oid> --json` | Exact selection, recoverable original bundle, native object validation and selected-ref CAS; see the command reference for historical request fields |
| Repo-local skills | `skills` proof gate | Proof result |

Repository source, tests, schemas, docs, official OpenSpec, and Attestations
remain above this map. Commitment is compiled transiently. The map routes work;
it does not create durable truth.

A compact reader may select coordination detail once. Completed detail has no
repeat-observation requirement. Follow a pending exact operation when one is
selected; otherwise stop that read without altering foreign ownership.

Review is not acceptance. Publish the selected trusted object to an explicit
proposal ref without inventing product proof or archiving unfinished intent.
Accepted/release targets retain their proof and closeout. Derive these meanings
from the current command, never a detached checkout name or a copied proof label.

Commit source and actual task progress before exact proof. Source acceptance,
delivery and Change completion are distinct: keep delivery obligations in the
same active Change and mark them only after observing their results. Archive
when those obligations are settled, using its governed continuation. Editing
tasks after proof makes a new source; ordinary Git commit does not finalize the
archive effect. A staged archive without valid source proof requires a current
recovery decision, not repeated commits or hook bypass.

Treat each peer effect as a new trust boundary. A preflight PASS or earlier peer
success does not authorize the next effect. Preserve applied peers, report
UNKNOWN honestly and re-observe current refs before replay; do not repair partial
publication by reconstructing or re-signing the product object.

For explicitly authorized historical repair, distinguish incorrect attribution
from an untrusted key or a Forge account association. Use exact original identity
fields, preserve legitimate authors and verify recovery before applying. Follow
the public repair continuation; do not substitute mailmap display changes, bulk
author replacement or hook bypass. Interrupted history signing reuses verified
native objects; a changed actor, ambiguous object or changed backup is not retry
permission. Reprove, rebind and observe each peer separately after the local CAS.
