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
| OpenSpec lifecycle | official `openspec` CLI | Official command JSON |
| Repo-local skills | `playbooks-v2` proof gate | Proof result |

Repository source, tests, schemas, docs, official OpenSpec, and Attestations
remain above this map. Commitment is compiled transiently. The map routes work;
it does not create durable truth.

A compact reader may select coordination detail once. Completed detail has no
repeat-observation requirement. Follow a pending exact operation when one is
selected; otherwise stop that read without altering foreign ownership.
