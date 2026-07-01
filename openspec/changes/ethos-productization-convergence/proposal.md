# Proposal: ETHOS Productization Convergence

## Summary

Converge ETHOS productization around a judgment-source kernel, a first-hour
adopter path, a five-command public workflow, a scorecard-only report surface,
and a DocOS authority graph read model.

## Motivation

ETHOS had strong repository governance mechanics, but its product entry still
mixed ontology, maintainer commands, campaign material, and self-audit success.
That made it harder for adopters to understand what ETHOS solves, what it does
not own, and how closeout should be proved.

## Scope

- Define `JudgmentSource` as the product judgment authority and make North Star
  language a derived reader view.
- Converge the canonical kernel chain to
  `JudgmentSource -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle`.
- Keep `Claim` as evidence binding rather than lifecycle owner.
- Split the command registry into public workflow, scorecard, and
  maintainer/reference commands.
- Rewrite first-hour docs around profile choice, dry-run, apply criteria,
  rollback, and the five-command loop.
- Add an authority graph read model with owner, canonical target, derivation,
  supersession, evidence references, and stable path.
- Support `python` as the current adoption profile name while preserving
  `python-package` as a compatibility alias.

## Non-goals

- Do not remove maintainer/reference commands.
- Do not turn DocOS authority graph data into a lifecycle owner.
- Do not hardcode dmgr raw/cache semantics in ETHOS core.
- Do not claim hosted CI, remote publication, or dmgr raw/cache parity from
  local product self-audit.
