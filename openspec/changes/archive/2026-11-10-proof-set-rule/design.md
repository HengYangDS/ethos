# Design

## Context

`GateRegistryDeclaration.validate_references` validates the proof sets with ids alone
(`_validate_proof_sets`). The rule needs each gate's `network_policy`, `kind` and `depends_on`,
because `proof_gates` runs `default`'s dependency closure. Committee round 2 (scratch
`gates-review/gate-efficacy-review-2.md`, Change B) found that only one direction of a derived rule
holds, and that the validator also judges governed repositories' profile declarations.

## Goals / Non-Goals

Goals: a narrower default proof can never need the network or a package build.

Non-Goals:

- moving the seven omitted offline gates into ETHOS's `default`, which would grow the readiness
  tier from 13 to 19 and needs its own measurement;
- deriving both sets from gate fields and deleting `proof_sets`, which the review named as the
  declarative end state and which needs its consumers checked first;
- a closed vocabulary for `kind`.

## Decisions

1. `_validate_proof_sets` receives the gates by id. When `default` differs from `full`, it walks
   `default`'s `depends_on` closure. Any gate there whose `network_policy` is not `offline`, or
   whose `kind` is `package`, refuses the registry with `default proof gate is not an offline
source check`.
2. A registry whose `default` equals `full` declares no narrower proof, so the rule does not
   apply. This keeps every governed repository's undeclared sets valid, including a networked
   gate such as aigw-cli's.

## Risks / Trade-offs

- A future registry that wants a networked gate in a narrower default must widen `default` to
  `full`, or move the gate out of `default`. That is the intended choice.
