# ETHOS OpenSpec Workspace

This workspace is the ETHOS case and specification carrier. It uses the
official OpenSpec workspace model with repository guardrails for proposal
intent, Commitment binding, active-carrier observation, and self-profile
authoring.

OpenSpec is the selected native carrier for the ETHOS self profile, but it is
neither mandatory for adopters nor a second ETHOS public command plane. The
official OpenSpec CLI owns workspace authoring, validation, and archival;
ETHOS consumes official active-carrier observations in `status`, `plan`,
`prove`, and `land` without re-exposing or predicting those operations.

## Product Protocol

```text
case = Commitment + proposal + design + tasks + spec deltas
```

- Accepted capability identity and behavior live only at
  `openspec/specs/<capability>/spec.md`.
- A proposal names each affected capability with exactly `subject`, `reuse`, and
  `change` intent.
- Active Change IDs are date-free lower-kebab identifiers that start with a
  letter; intent lives under `openspec/changes/<change-id>/`.
- Changed behavior lives in that Change's delta specs.
- `commitment.toml` and its Commitment own active intent, repository subject,
  scope, invariants, acceptance, permissions, and publication policy.
- Historical carriers use exactly one archive date:
  `openspec/changes/archive/YYYY-MM-DD-<change-id>/`.
- Archived changes are history after closeout, not reusable active work
  containers.

Every non-trivial self-profile governance mutation should have one selected
active Change. A completed Change remains active and blocks integration until
the owner-native archive operation removes it from official active state.

## Proof

Validate the carrier with its native owner, then compile the governed plan:

```bash
openspec validate --all --strict --json
ethos plan --changed --json
```

ETHOS validates proposal intent, accepted spec identity, Commitment binding,
and scope while consuming official `doctor`, `list`, `status`, and strict
`validate` observations. ETHOS does not invoke or predict archive. Historical
archive bytes remain non-authorizing history and are not re-evaluated to decide
a current transition.
