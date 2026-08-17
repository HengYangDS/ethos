# Change: Preserve bounded adopter reader compatibility

## Why

Current AIGW and codex-responses-proxy profiles contain the former
`[[branch_roles.transitions]]` declaration and a terminal schema-v1 repository
Commitment. The accepted ETHOS source removed both readers at once, so a newer
package runtime rejects otherwise healthy adopters before `status` or `plan`
can explain the migration boundary. Selecting older runtimes by trial execution
is not a product contract.

## What Changes

- Admit the exact deployed transition declaration shape in the loose
  branch-role reader while discarding it from the current mutation model.
- Keep strict branch-role admission closed to that retired declaration and
  reject unknown fields or malformed values.
- Let read-only `plan` project an exact terminal-v1 repository Commitment with
  carrier-byte and legacy semantic digests, while explicitly denying proof and
  mutation authority and omitting a v2 `TransitionPlan`.
- Add a source-hidden wheel regression that exercises the deployed profile and
  Commitment shapes through installed `status` and `plan` commands.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=adopter reader compatibility; reuse=extend;
  change=modify; facet:lifecycle=inspection,planning,migration;
  facet:surface=cli,profile,package; facet:authority=source,test,openspec.

## Impact

- Affects branch-role parsing, repository planning, package-only smoke, and
  focused command regressions.
- Does not restore the retired role-transition executor, parse v1 as v2,
  authorize proof or Git effects, or mutate AIGW/Proxy.
- Proxy retired-Lease proof selection remains a separate successor Change.
