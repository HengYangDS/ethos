# Proposal

## Why

ETHOS fixes its tunable values in code, so a governed repository whose content needs a different
value has no lawful way to say so, and a proof does not record which value it ran under.

- GitLab issue #2 (Ordo, 2026-10-30): release-tests ran 578.7 s of a hard-coded 600 s; the adopter
  could not raise it, and a timeout surfaced as a missing report. `test-runner-unification` and
  `native-outcome-evidence` (both in alpha.26) already let a gate declare `timeout_seconds` and fail
  as `gate_timeout` with its bound and elapsed time. The issue's items 2 and 4 remain: the effective
  value is not in the proof's evidence, and every other duration is fixed.
- At `d747b77c6`, `src/` holds 74 numeric `timeout=` literals in 37 modules and three timeout
  constants, from 0 to 600 seconds, none declared, none bounded, none overridable, none recorded;
  `tools/` holds 29 more.
- On 2026-11-01 the owner asked that ETHOS remove hard-coding globally in favour of configuration,
  and that governed repositories may use different parameters for timeouts and other settings.
- The per-file size ceilings already follow the rule this needs
  (`src/ethos/repository/paradigm/size.py`): a packaged default and bound, a repository value in
  `.ethos/rules.toml` that applies when stricter, or looser within the bound with a reason, and a
  gap that never widens the value. That rule exists once, for one group.

## What Changes

- The paradigm declares every tunable value as a parameter row: its group, key, default, unit and
  the bound beyond which no repository may loosen it. The size ceilings become the `size` group,
  with their keys and behaviour unchanged.
- One resolution rule, the size rule generalized, resolves every group from `.ethos/rules.toml`
  `[paradigm.<group>]` and `[paradigm.<group>.reasons]`.
- Product code reads each value through one accessor, resolved once per invocation for the target
  repository. Values that are protocol constants, such as a non-blocking lock attempt, become named
  constants or native arguments and are not parameters.
- Every gate runs under a deadline: its declared `timeout_seconds`, held to the `timeout` group's
  bound, or the repository's `timeout.gate_seconds`. Commands inside a gate run within it.
- Each proof records, per gate, the timeout it ran under and its source, and the proof summary lists
  every looser repository value with its reason.
- An architecture check counts numeric timeout literals and timeout constants in `src/` and
  `tools/`; it is 0 for `src/` when this Change lands and its recorded `tools/` count only falls.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: declared parameters with one resolution rule, of which the size ceilings
  are one group.
- `quality`: every gate runs under a deadline, and proofs record the effective timeout of each gate
  and the repository's looser values.

## Impact

`src/ethos/contracts/paradigm/paradigm.toml` and its model, `src/ethos/repository/paradigm/size.py`
(generalized), the command composition root, every module that holds a timeout literal (listed in
the design), the gate runner's deadline and evidence, one architecture test and the two
specifications. Governed repositories see no change unless they declare a value or run a gate longer
than 600 seconds without declaring its timeout; GitLab issue #2 is answered with the release that
carries this Change.
