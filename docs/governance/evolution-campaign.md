---
subject: ethos:learning-relations
role: explanation
state: active
relations:
  projects:
    - product-design-contract.md#recursive-domain-feedback
---

# Learning And Change Relations

Status: explanatory projection.

Purpose: explain how research and related Changes remain available without a
parallel lifecycle authority.

See also: [Product Design Contract](product-design-contract.md) and
[Command Plane](../reference/command-plane.md).

Research questions, procedures, and declared dependencies remain in official
OpenSpec proposal, design, spec, task, or configuration artifacts. Observations,
judgments, proofs, and effects belong to content-addressed Attestations. Any
multi-change view is derived from official artifacts, Git history, current
Facts, and selected Attestations.

There is no separate ledger, mutable program state, step/closeout database, CEL
plane, or command family for this purpose. Historical ledgers and records remain
immutable bytes and cannot participate in a current verdict.

Current progress comes only from the selected active Change's official
`tasks.md`. A derived relation view may explain ordering but cannot select work,
mutate task state, or make archive bytes current.

`ethos status --json` projects current lifecycle gaps. `ethos prove --full
--json` evaluates the configured local proof plan. `ethos land --json` and
`ethos publish --json` consume their own current readiness facts.

A research statement or dependency relation is not proof by itself. An accepted
result remains bound to the compiled Commitment, exact HEAD, TransitionPlan,
evidence, and Attestation verdict.

## Recursive Feedback In Each Repository

The [product contract](product-design-contract.md#recursive-domain-feedback)
owns this capability. Self-hosted quality improvement and adopted-domain
improvement follow the same protocol without sharing business authority.

| Lens | Question | Existing carrier to revise |
| --- | --- | --- |
| Actual use | Does the delivered result satisfy the repository's real need? | Domain-owned intent, outcome evidence and user-facing behavior. |
| Methods | Are implementation, tools and procedures effective and economical? | Implementation, native configuration and applicable Skills. |
| Governing models | Do the abstraction, rules and acceptance model preserve necessary distinctions? | The owning model and its executable consumers. |
| Purpose and assumptions | Are the problem framing and success criteria still justified? | Authorized intent alignment and the repository's product contract. |

A failed implementation is not automatically a model gap. Repeated failure,
incompatible constraints or technically green but ineffective outcomes require
checking that distinction before another local patch. A justified promotion
changes the smallest sufficient upper boundary, migrates its consumers and
verifies both the distinguishing counterexample and retained valid behavior.
The same scrutiny applies to feedback collection, interpretation and judgment.

Domain Skills and observers provide business-specific expertise and evidence.
They do not own goals, completion or repository permissions. Missing or stale
business observations leave that outcome claim open; they need not prevent an
independently admissible source change. A domain failure can propose a shared
ETHOS repair without copying a local parser, metric set or business model into
other repositories. No additional learning ledger is required.
