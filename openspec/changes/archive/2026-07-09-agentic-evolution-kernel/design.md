# Design

The Agentic Evolution Kernel keeps ETHOS as the trust kernel underneath external
agentic tools.

The design separates four layers:

1. board / collaboration plane;
2. event / automation plane;
3. execution plane;
4. truth / evidence plane.

Git, source, tests, schemas, OpenSpec, evidence, claims, and chronicle remain
repository truth. ETHOS governs admission, proof, claim, chronicle, land, and
publication-readiness transitions over that truth; external planes receive only
read models, intake projections, or bounded dispatch contracts.

ETHOS gates and reports publication readiness. Remote publication and release
require the configured human or release authorization.

The design absorbs useful mechanisms from managed-agent platforms without
absorbing their sovereignty:

- agents as assignable, observable participants;
- issue-to-agent lifecycle telemetry;
- runtime capability profiles;
- recurring autopilots as intake triggers;
- skill compounding as candidate learning after tracked promotion;
- dependency-aware task graphs and ready queues;
- provider branch / pull-request / merge-request output as candidate material.

It rejects the following as product ontology:

- board state as lifecycle truth;
- issue assignment as mutation authority;
- agent output as repository truth;
- task completion as proof;
- external skill memory as chronicle;
- vendor-specific lifecycle grammar as ETHOS lifecycle.

The staged ladder is:

1. observe signals;
2. normalize intake envelopes;
3. dedupe and classify issue candidates;
4. project candidates to external boards only as dry-run or authorized
   projections;
5. create dispatch envelopes for admitted changes;
6. invoke execution backends within capability levels;
7. import result packages;
8. prove, claim, chronicle, and move repeated failures upstream.

The first safe implementation slice is read-only intake mining. Issue raising,
agent assignment, backend execution, result import, and upstream guardrail
generation belong to later Work Lanes.

The terminal flow is:

```text
signal -> intake envelope -> issue candidate -> admitted change -> Work Lane + claim -> agent invocation -> result package -> proof -> land / publication-readiness / authorized publish -> chronicle -> evolution decision
```

Every arrow is a type conversion. No external signal should slide directly into
mutation, claim, or publication.

Proof strategy for this design change is static and evidence-bound:

- changed-path playbook routing selects the change lifecycle skill;
- OpenSpec lifecycle sees the active carrier;
- claim and chronicle evidence bind this planned design to a reviewable claim;
- current root-bound `ethos plan --changed --json`, `ethos prove --json`, and
  `ethos report --json` show readiness and remaining gaps. `ethos prove --json`
  is readiness unless a later Work Lane explicitly runs executed proof with an
  expected HEAD.

Implementation of proposed future intake mining, issue raising, dispatch
planning, backend execution, and result-package import belongs to later Work
Lanes.
