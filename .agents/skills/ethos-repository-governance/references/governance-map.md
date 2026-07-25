# Governance Command Map — ETHOS Repository Governance

Skill-specific map of which ETHOS command governs which concern. A lookup for
choosing the right command; the live `ethos <cmd> --help` and the command JSON remain
authoritative.

## The loop (state transitions)

| command | concern | mutates? |
| --- | --- | --- |
| `status` | checkout role, dirty state, write-readiness gaps | no |
| `plan --changed` | which rules match changed paths, which gates are required | no |
| `prove` | readiness; `prove --execute` mints HEAD-bound executed proof | only `--execute` writes a proof record |
| `land` | fast-forward the work lane to the candidate role | `--apply` mutates (enforced) |
| `publish` | local publication readiness | `--apply` mutates (enforced) |
## Governance surfaces (read-only reports)

| command | governs |
| --- | --- |
| `audit --mode shape` | repository shape: packages, docs, schemas, playbooks, claims |
| `rules check` / `rules eval` | rule→gate matching and rule-fact evaluation |
| `quality <tool>` | determinism gates (types, markdown-links, shell, toml, yaml, docs) |
| `quality claims` | claim/evidence binding and HEAD-freshness |
| `parity gaps` | adopter capability-parity ledger |
| `playbooks check` / `playbooks route` | skills registry validity and intent routing |
| `openspec` | OpenSpec change lifecycle state |

## Work Lane lifecycle

| command | step |
| --- | --- |
| `lane start` | create the work lane + lease (arms admission) |
| `lane prewrite <paths>` | write-admission check before a tracked write |
| `land --closeout` | promote candidate to the accepted root |
| `lane retire-landed` | remove a fully-landed lane + release its lease |

## Authority order (who wins on conflict)

Read `system/authority.toml`: user instruction outranks contracts, which outrank
generated projections. A generated surface never outranks its source. Skills are
projections — repository truth (source/tests/schemas/docs/OpenSpec/claims/evidence
and command JSON) is always higher authority than skill text.
