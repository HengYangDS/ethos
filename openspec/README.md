# ETHOS OpenSpec Workspace

This workspace is the ETHOS case and specification carrier. It uses the
official OpenSpec workspace model and adds ETHOS product guardrails for
capability ownership, proposal metadata, claim/evidence binding, archive
closeout, and adopter scaffolding.

OpenSpec is mandatory governance for promoted specification records, but it is
not a second ETHOS public command plane. Humans and agents enter through
`ethos ...`; ETHOS delegates to the official OpenSpec CLI for doctor, status,
archive, and strict validation when specification health must be proved.

## Product Protocol

```text
case = proposal + design + tasks + spec deltas + claim/evidence refs
```

- Current accepted behavior lives under `openspec/specs/<capability>/spec.md`.
- Capability routing metadata lives in `openspec/specs/<capability>/capability.toml`.
- Capability family vocabulary lives in `openspec/specs/families.toml`.
- Active change intent lives under `openspec/changes/<change-id>/`.
- Archived changes are history after closeout; they are not reusable active work
  containers.

Every non-trivial governance mutation should have a non-complete active change
or an explicit attachment to one. Complete changes are historical records unless
a governance decision reopens the work.

## Proof

Use ETHOS first:

```bash
ethos openspec --lifecycle --json
```

The report composes official OpenSpec validation with ETHOS lifecycle checks for
proposal metadata, direct capability routing, claim binding, and archive health.
