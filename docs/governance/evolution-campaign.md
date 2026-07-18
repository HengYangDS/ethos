---
subject: ethos:evolution
role: explanation
state: canonical
relations:
  canonical_for: repository governance
---

# Evolution Campaign

ETHOS governs repository evolution through one repository-truth ledger at `evolution/ledger.toml` plus campaign manifests under `evolution/campaigns/`. Documentation explains the mechanism; it does not store a parallel ledger.

ETHOS governs repository evolution as a judgment loop, not as a pile of
independent mechanisms:

```text
question -> boundary -> hypothesis -> experiment/review -> proof -> judgment -> inscription or release
```

The more fundamental movement is the **governed passage** from a question to a
repository commitment, bounded refusal, archive, or retirement. A **governed
practice claim** is the evolution carrier for that passage. It names the
subject, question, claim, boundary, falsifiers, relation to incumbents,
candidate set, experiment, evaluation, commitment targets, commitment effect,
and fate records. Hypotheses, candidate sets, experiments, evaluations, practice
changes, campaign steps, runtime nodes, and scorecards are projections that help
test and promote that claim. They are not the center.

The root discipline is:

```text
以问定域，以实践为器，以证据验道，以承诺成法，以退藏去执
```

In operational terms: research and experiments are vessels, not authorities; a
question must be bounded before it can be tested; evidence tests whether a
practice deserves trust; a proven practice becomes a repository commitment only
through source, schema, docs, OpenSpec, claims, evidence, and Chronicle;
obsolete, false, redundant, stale, misbounded, or overreaching practices must be
retired, rejected, or archived instead of preserved as process residue.

Repository audit checks command-plane growth, package ontology drift, docs metadata,
schema coverage, profile leakage, and adapter boundaries. Evolution records
must either canonize a proven improvement or retire it.

Evolution uses the governed repository model. It reuses the same governance
context, command semantics, evidence contracts, and mutation discipline for
every profile.
`ethos audit` changes proof depth for the product-toolchain profile; it does
not create a private command plane or a second product lifecycle.

`ethos campaign hypotheses --json` reads `evolution/ledger.toml` and exposes active hypotheses as first-class
objects. A hypothesis should be challenged, proven, canonized, or retired; it
must not linger as implicit roadmap text.

The same ledger also admits first-class practice-evolution records. ETHOS does
not ultimately govern tools or mechanisms as objects of attachment; it governs
which questions may become trustworthy commitment effects:

- `practice_claim`: the practice-evolution carrier inside a governed passage.
  It binds the subject, question, claim, boundary, falsifiers, candidate set,
  experiment, evaluation, practice-change refs, commitment targets, evidence refs,
  and decision refs;
- `candidate_set`: a bounded set of competing practices, frameworks, adapters,
  method packs, projections, or implementation strategies answering the same
  governance question;
- `experiment_protocol`: variables, controls, metrics, stop conditions, failure
  conditions, and evidence refs for testing one or more hypotheses;
- `evaluation_record`: evidence-weighted comparison, selected candidate,
  rejected candidates, metric results, and decision refs;
- `practice_change`: the judged fate of a practice: introduce when there is no
  incumbent, compose when several carriers are deliberately combined, refine
  when an existing practice is improved in place, supersede only when a new
  practice covers and replaces an incumbent boundary, retire when an incumbent
  is redundant/unsafe/wrong, and reject when a candidate remains bounded
  learning.

This makes multi-candidate selection, introduction, composition, refinement,
real supersession, retirement, rejection, and archive part of repository truth
rather than assistant narrative. The objects still do not create a second
lifecycle: all practice evolution must bind to source, schemas, OpenSpec,
claims, evidence, and Chronicle before it becomes canon.

The fate terms are intentionally asymmetric. Introduction is valid only when no
incumbent owns the boundary. Composition keeps multiple bounded carriers.
Refinement improves a valid incumbent in place. Supersession requires an
incumbent, coverage of that incumbent's responsibility boundary, migration,
fallback, kill signal, evidence, and retirement conditions. Retirement removes a
redundant, unsafe, false, stale, misbounded, or overreaching incumbent. Rejection
keeps a candidate as bounded learning without promotion. Archive preserves
judged learning after the carrier no longer participates in active governance.

`ethos quality evidence-freshness --json` checks the ledger as part of the
evidence freshness read model. Active hypotheses must cite resolvable proof,
review, and decision references. Proof references may be known ETHOS command
references; review and decision references are repository paths. Reviewed
non-campaign evolution entries must bind at least one evidence reference and one
decision reference, so structural evolution cannot become a second narrative
store detached from claims, chronicle, and repository truth.

`evolution/campaigns/<campaign-id>/campaign.toml` records long-running product
work as an ordered campaign manifest. A campaign is not a giant Work Lane. It
is an orchestration record whose steps name the OpenSpec change, Work Lane
branch, claim, evidence refs, and closeout state that must be completed before
later steps depend on them. Each step lands through normal Work Lane semantics:
prove, land to candidate, closeout-apply to the accepted root, then retire the
lane.

`ethos campaign status --json` exposes those manifests as the canonical campaign
read model. Planned future steps may name their intended OpenSpec changes before
the carriers exist. An active, in-progress, or landed step must resolve to its
active carrier under `openspec/changes/`; a closed or retired step must resolve
to its archived carrier and terminal closeout record. A campaign may await its
next planned step with no active lane; the reader exposes that successor rather
than inventing an active lane. Any state/carrier disagreement is a required
campaign gap, not an advisory display detail.

`ethos campaign closeout --json` exposes the local campaign closeout package. It
is a read-only aggregation of Work Lane closeout support, publication readiness,
release policy, campaign manifests, unresolved parity packages, and shadow
parity execution plans. Remote publication remains deferred until an adapter is
available; local campaign closeout still proceeds through the configured
candidate branch and a local fast-forward of the accepted root.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
