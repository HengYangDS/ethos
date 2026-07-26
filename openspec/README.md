# ETHOS OpenSpec Workspace

This workspace is the ETHOS case and specification carrier. It uses the
official OpenSpec workspace model and adds ETHOS product guardrails for
capability ownership, proposal metadata, ChangeContract binding, archive
closeout, and adopter scaffolding.

OpenSpec is mandatory governance for promoted specification records, but it is
not a second ETHOS public command plane. Humans and agents enter through
`ethos ...`; ETHOS delegates to the official OpenSpec CLI for doctor, status,
archive, and strict validation when specification health must be proved.

## Product Protocol

```text
case = ChangeContract + proposal + design + tasks + spec deltas
```

- Current accepted behavior lives under `openspec/specs/<capability>/spec.md`.
- Capability routing metadata lives in `openspec/specs/<capability>/capability.toml`.
- Capability family vocabulary lives in `openspec/specs/families.toml`.
- Active Change IDs are date-free lower-kebab identifiers that start with a
  letter; intent lives under `openspec/changes/<change-id>/`.
- Historical carriers use exactly one archive date:
  `openspec/changes/archive/YYYY-MM-DD-<change-id>/`. A Change ID itself does
  not carry a terminal `YYYYMMDD` suffix.
- Archived changes are history after closeout; they are not reusable active work
  containers.
- `contract.toml` owns active intent, repository subject, scope, invariants,
  acceptance, permissions, and publication policy for each Change.

Every non-trivial governance mutation should have a non-complete active change
or an explicit attachment to one. Complete changes are historical records unless
a governance decision reopens the work.

## Proof

Use ETHOS first:

```bash
ethos openspec --lifecycle --json
```

The report composes official OpenSpec validation with ETHOS lifecycle checks for
proposal metadata, direct capability routing, ChangeContract binding, and archive health.
For every active change, it runs the configured official archive in a disposable
workspace copy and projects any official application-time diagnostic without
mutating the source workspace. The same preflight blocks `ethos plan --changed`,
`ethos prove`, and `ethos land` until the delta is archiveable.
