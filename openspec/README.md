# ETHOS OpenSpec Workspace

This workspace is the ETHOS case and specification carrier. It uses the
official OpenSpec workspace model with repository guardrails for proposal
intent, ChangeContract binding, archive closeout, and adopter scaffolding.

OpenSpec is mandatory governance for promoted specification records, but it is
not a second ETHOS public command plane. The official OpenSpec CLI owns workspace
authoring, validation, and archive syntax; ETHOS consumes active carriers in
`plan`, `prove`, and `land` without re-exposing those commands.

## Product Protocol

```text
case = ChangeContract + proposal + design + tasks + spec deltas
```

- Accepted capability identity and behavior live only at
  `openspec/specs/<capability>/spec.md`.
- A proposal names each affected capability with exactly `subject`, `reuse`, and
  `change` intent.
- Active Change IDs are date-free lower-kebab identifiers that start with a
  letter; intent lives under `openspec/changes/<change-id>/`.
- Changed behavior lives in that Change's delta specs.
- `contract.toml` and its ChangeContract own active intent, repository subject,
  scope, invariants, acceptance, permissions, and publication policy.
- Historical carriers use exactly one archive date:
  `openspec/changes/archive/YYYY-MM-DD-<change-id>/`.
- Archived changes are history after closeout, not reusable active work
  containers.

Every non-trivial governance mutation should have a non-complete active change
or an explicit attachment to one. Complete changes are historical records unless
a governance decision reopens the work.

## Proof

Validate the carrier with its native owner, then compile the governed plan:

```bash
openspec validate --all --strict --json
ethos plan --changed --json
```

ETHOS validates proposal intent, accepted spec identity, ChangeContract binding,
scope, and archiveability while compiling the plan. The same preflight blocks
`plan`, `prove`, and `land` until the delta is archiveable.
