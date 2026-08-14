## Why

ETHOS currently implements one repository transition several times: commands,
Git effects, Lease storage, hook admission, package runtime selection, proof,
and publication each reconstruct part of the lifecycle and then attempt to
repair disagreement. The observed failures are therefore not independent bugs;
they are lossless-model failures caused by duplicated transition ownership.

The terminal correction is a model promotion, not another compatibility layer.
ETHOS needs one declarative transaction spine whose immutable inputs and outputs
are shared by every lifecycle command:

```text
observe -> derive receipt -> exact-CAS apply -> post-observe -> attest
```

Only Commitment and Attestation remain durable semantic roots. Facts,
TransitionPlan, operation authority, receipts, continuations, status, Lease
views, hook views, runtime views, and provider views are derived projections.

## What Changes

- Replace reusable Commitment permissions with exact operation-bound authority
  derived from the selected declaration, actor, current facts, and requested
  effect.
- Make one pure reducer compile every lifecycle operation into one immutable,
  content-addressed receipt with exact preconditions, effects, compensations,
  postconditions, and continuation.
- Make apply consume only that receipt, perform exact compare-and-swap effects,
  post-observe the complete transition, and issue an Attestation. A partial
  effect remains resumable through the same receipt; it is never reported as
  terminal success.
- Migrate refresh-base first, proving that ref, Lease, attachment, and receipt
  cannot silently diverge. Then move land, role transition, retirement,
  Commitment rebind, hook/runtime convergence, proof, publication, and history
  replacement onto the same reducer and delete their duplicate orchestration.
- Bind source, package, schemas, help, hooks, and runtime selection to one
  immutable package manifest and one structured result envelope.
- Keep adopter policy declarative: branch roles, commit policy, gates, provider
  identity, signing, and projection topology are repository declarations;
  ETHOS owns compilation, validation, exact effects, and evidence.
- Retire Campaign orchestration and any parallel lifecycle/task store. This
  Change's `tasks.md` is the sole implementation task graph.
- Preserve the already implemented formatter-safe Markdown parsing,
  repository-declared commit-message execution, Conventional lifecycle
  subjects, and four-hook convergence as projections of the same terminal
  model.

## Capabilities

### Modified Capabilities

- `kernel`: one reducer and one receipt-bound transaction algebra.
- `contracts`: operation-bound authority and immutable receipt/result contracts.
- `command-plane`: lifecycle commands become projections over the reducer and
  return one structured continuation envelope.
- `adapters`: effects execute exact receipts and expose typed partial recovery.
- `repository-governance`: Work Lane, Lease, transition, retirement, history,
  and provider projection share one transition owner.
- `proof-hosts`: required gate execution and provider observations remain
  explicit, independent attestations.
- `distribution`: source/package/schema/help/runtime/hook identity and portable
  runtime health converge through one manifest.
- `quality`: one commit semantics owner and positive, complete gate execution.

### Removed Capabilities

- Campaign manifests, Campaign lifecycle state, Campaign command authority,
  reusable Commitment permissions, compatibility readers, and command-local
  lifecycle state machines.

## Impact

This is an intentional destructive cutover. Existing state and declarations are
not preserved through dual readers or aliases. The accepted package exposes one
public migration/recovery operation that observes current Git truth, derives an
exact receipt, and either establishes the terminal model or fails closed without
claiming success. AIGW, Proxy, and other adopters remain unmodified until their
owners execute accepted package-only receipts.
