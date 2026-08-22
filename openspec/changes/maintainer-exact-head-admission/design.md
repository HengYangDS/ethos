## Context

See `proposal.md` for the observed failure. ETHOS already owns exact candidate
proof selection, candidate-to-accepted TransitionPlan compilation, prepared ref
intent, Git CAS, post-observation, Attestation, external receipt validation, and
local-only publication topology. The defect is composition: closeout and Git
hooks re-derive overlapping policy, while remediation is produced separately
and sometimes contains placeholders.

## Goals / Non-Goals

**Goals:**

- Make existing `ethos land --closeout` the one accepted-head admission owner.
- Represent one immutable closeout resolution that binds exact accepted and
  candidate coordinates, proof plane, receipt validation, mutation decision,
  prepared ref intent, and next command.
- Make hook and reader surfaces consume or project that resolution.
- Delete duplicate hook-local proof/topology decisions and placeholder actions.
- Preserve exact-CAS, candidate semantic evaluation, control-replacement proof,
  developer proposal behavior, and local-only operation.

**Non-Goals:**

- A new `admit` or generic role-transition command.
- A Forge lifecycle database, hosted-proof authority, compatibility alias, or
  hook bypass.
- Changes to adopter repositories, supply-chain versions, performance, or the
  broader repository compression backlog.

## Decisions

### Closeout owns one typed resolution

Promote the existing closeout evaluation into one typed immutable result. It
contains the exact repository root, accepted ref/head, candidate ref/head/tree,
selected proof identity and plane, validated optional external receipt,
signature facts, lifecycle/audit verdicts, ref-intent coordinates, aggregate
verdict, and executable next command. Dry-run serializes it; apply re-observes
the same coordinates and consumes it to compile and execute the existing Git
effect.

Alternative rejected: add `ethos admit`. That duplicates the public role
transition owner and allows closeout, hooks, and admission to diverge again.

### External receipts are typed inputs to proof admission

The existing provider-neutral receipt is validated against the closeout subject
before the mutation decision. Its identity participates in the plan closure and
effect Attestation, but it remains `mints_authority=false`; explicit operator
authorization and effect-time Git facts still gate mutation.

Alternative rejected: persist a Forge approval store or infer approval from CI
status. Both create parallel truth and weaken offline recovery.

### Hooks verify the prepared effect, not a second workflow

Reference-transaction consumes the prepared ref intent already written by the
closeout executor and still evaluates candidate-tree semantics. Pre-push
validates the exact locally admitted object and publication target. It no longer
requires a protected local ref to have moved before the same object can be
pushed, because local closeout and remote publication are separate exact effects.

Alternative rejected: special-case bypass environment variables. They are not
auditable product capability and encourage raw hook disablement.

### One next-action formatter owns remediation

The closeout resolution renders a complete command from its current
coordinates. Status, plan, land, and hooks project the same value. Receipt
requirements use the concrete requested path or generated package location;
commands never contain `<...>` placeholders.

### Forge presence is profile data, not a universal precondition

The proof plane is selected by current repository profile. A local-only profile
uses exact local proof and signature facts. A protected provider receipt is
required only where the selected policy says so. No branch in the kernel
manufactures hosted success.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| `adapters:Protected ref hooks bind semantic evaluation to promoted control` | `2.3` | accepted-ref and pre-push producer-to-consumer tests |
| `command-plane:Public Command Plane` | `2.4` | closeout/status/plan/hook next-action contract tests |
| `repository-governance:Accepted-root closeout is bound to one audited candidate HEAD` | `2.1`, `2.2` | exact local/external subject and CAS black-box tests |

## Risks / Trade-offs

- [Risk] Reusing an external receipt for a different candidate or policy →
  Mitigation: validate every identity field against freshly observed closeout
  coordinates and bind the validated receipt digest into the plan.
- [Risk] Removing pre-push local-ref equality weakens protected publication →
  Mitigation: require proof of the exact pushed object plus the accepted
  closeout effect/Attestation rather than equality as a proxy.
- [Risk] A typed resolution becomes another durable state object → Mitigation:
  keep it transient; durable truth remains Commitment, Git, and Attestation.
- [Risk] Candidate evaluator and accepted shell disagree → Mitigation: retain
  candidate-tree runner binding and fail closed when it cannot be established.

## Migration Plan

1. Add black-box and producer-to-consumer RED cases for exact local/external
   closeout, circular pre-push rejection, and executable remediation.
2. Introduce the typed closeout resolution inside the current land/mutation
   owner and route dry-run/apply through it.
3. Route hooks and readers to the shared decision/projection and delete their
   duplicate proof/topology/local-ref checks.
4. Run strict OpenSpec, focused and full quality proof, archive the Change, land
   it through the public exact-CAS path, and verify the accepted runtime.

