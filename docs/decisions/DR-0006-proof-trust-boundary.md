---
subject: ethos:decision:proof-trust-boundary
role: decision
state: canonical
relations:
  depends_on: DR-0005
  informs: hosted-enforcement receipt path, independent-verification provider contract
---

# DR-0006: Proof Trust Boundary and Optional Independent-Identity Verification

Status: accepted.

Purpose: fix the honest meaning of a local executed-proof record (a `local_readiness`
claim, not an enforcement guarantee), reject an on-host MAC as security theatre under the
same-UID threat model, and specify the optional, default-off independent-identity
verification plug (lightweight local daemon or hosted forge) as the genuine anti-forgery
trust root.

See also: [Decision Records](README.md) and [Decision Index](decision-index.md).

## Record

| Field | Value |
| --- | --- |
| Decision ID | DR-0006 |
| Kind | architecture / security |
| Status | accepted |
| Decision Date | 2026-07-10 |
| Decision Version | 3 |
| Decision Change Date | 2026-07-31 |
| Class | architecture / security |
| Scope | What a local executed-proof record does and does not guarantee; where the genuine anti-forgery trust root lives; the optional verification adapter interface. |
| Supersedes | none |
| Superseded By | none |
| Depends On | DR-0005 (declarative lifecycle spine) |

## Context

ETHOS governs autonomous agents that run as the **same OS user** as the human operator.
The local executed-proof carrier is a content-addressed proof Attestation under
`.ethos/state/attestations/<attestation-id>.json`. Admission validates one self-contained
closure over the exact Commitment, Facts, policy, transient TransitionPlan, proof operation,
and digest-addressed checks artifact under `artifacts/<sha256>.json`. It does not replay a
historical workflow: it validates the carried closure, the current Git tree at the attested
HEAD, and either the canonical default or full repository proof policy.

Those checks remain **same-UID local evidence**: the governed agent can author files that
the same UID may also verify. Content addressing and exact bindings detect partial edits,
bit-rot, wrong-HEAD copies, stale policy, and artifact tampering, but they are not a trust
boundary against that principal. The retired head-keyed proof file is inert, and current
tests pin exact Attestation identity, plan binding, and fail-closed artifact validation.

A multi-agent, `local-first`, offline workflow (multiple git worktrees driving parallel
agents) is a **first-class** scenario, not an edge case. It must not depend on network or
a hosted forge. This raises the sharp question: can a same-machine trust root exist?

Cryptographic reality: **under a single UID there is no trust boundary.** Any signing key
an on-host verifier can read, the same-UID adversary can also read, `ptrace`, or bypass by
rewriting the verifier. An on-host MAC/signature therefore raises attacker *effort*
(edit-a-file → read-a-key) but not the *trust boundary*, while adding a
universal-forgery-on-key-leak blast radius strictly worse than today's bounded per-file
forgery. A genuine boundary requires an **independent identity** the agent cannot write —
either a separate local OS identity, or a hosted forge — that **re-executes** the gates.

## Decision

1. **The local proof Attestation is a `local_readiness` claim, never an enforcement/prevention
   guarantee.** Consumers must not surface a valid local record as "enforced" or
   "prevented". Exact Commitment, Facts, policy, plan, operation, HEAD, and artifact
   bindings are the real and sufficient job of the local layer. The operation identity is
   the canonical digest of `proof.execute`, Commitment, Facts, policy, and the dependency-
   complete DAG. Artifact identity is the SHA-256 of the exact checks bytes carried through
   `evidence_refs`; equivalent executions may have different artifacts without changing
   operation identity.

2. **No keyed MAC / signature is added to the local proof record.** Under the same-UID
   threat model it is security theatre and enlarges blast radius. Rejected deliberately.

3. **The genuine anti-forgery trust root is re-execution under an independent identity**,
   expressed through the signed `IndependentVerificationReceipt` /
   `independent_verification_admission_report` path.
   Two interchangeable *plugs* implement one interface:
   - **Hosted plug** (networked): a forge `pre-receive` re-executes the required floor and
     mints a signed receipt. Requires network; used only at publication/share.
   - **Local independent-identity plug** (offline): a lightweight local verifier under a
     **dedicated OS user** the agents cannot read, re-executing the floor and writing an
     agent-readonly receipt. Preserves `local-first` and offline multi-agent.

4. **Verification is OPTIONAL and default-OFF.** A repository that sets no
   `require_*_enforcement` runs on `local_readiness` alone — zero adopter burden, no daemon,
   no network. Enforcement is opt-in per repository. This upholds the generic-product /
   no-hardcoded-basis rule: ETHOS ships the interface, never a mandatory verifier.

5. **Any local verifier implementation is restricted to the LIGHTWEIGHT path**
   (operator constraint): a single dedicated OS user (e.g. `ethos-verifier`) + one launchd/
   systemd daemon + a private key at `chmod 600` unreadable by the agent user. Agents write
   a request to an inbox they can only append to; the daemon re-executes the pinned,
   out-of-tree ETHOS floor (never the requesting tree's own `ethos` package — the
   judge-is-judged hole) and writes a signed receipt to an agent-readonly path. Per-agent
   containers / per-agent OS users are **out of scope** — one independent verifier identity
   suffices; agents may still share the operator's account. The product owns this receipt
   contract, not a bundled provider executable or deployment recipe.

6. **Proof does not mint mutation authority.** Proof admission establishes correctness for
   one exact operation closure. Mutation consumers derive authority independently:

   | Proof or consumer | Authority |
   | --- | --- |
   | Focused proof | Observation only; never satisfies repository proof or mutation admission. |
   | Default repository proof | Admits the exact default policy closure. It supports candidate integration only when its plan matches freshly derived Lease-bound authority. |
   | Full repository proof | Admits the exact full policy closure. It grants no authority beyond the default proof. |
   | Candidate transition | Admits the current proof set, derives authority from the current Work Lane Lease, then compiles a separate Git-CAS plan from fresh repository, HEAD/tree, ref, actor, and Lease-generation facts; proof nodes never become the mutation plan. |
   | Accepted transition | Authorizes the Git effect only from the pre-transition accepted-root Commitment; candidate bytes cannot grant accepted-root authority. |

7. **Execution identity follows the admitted DAG.** Gate policy is resolved from
   `plan.facts.head`; every runner node command must equal the corresponding policy execution
   identity before invocation; and dependency closure is canonicalized topologically before
   operation identity is computed.

## Consequences

- ETHOS stops over-claiming: local proof is a readiness assertion; a successful land also
  records one bounded local Git effect. Neither constitutes independent enforcement. Solo
  and same-UID multi-agent users get exactly that, with no new moving parts.
- The optional plug has a provider-neutral exact-receipt contract and no bundled
  provider executable. It remains default-off: implementation, installation,
  provider-local trust anchors, key ownership, and any daemon, hook, or hosted
  service remain operator choices rather than product defaults.
- Provider-native identity and hosted-enforcement artifacts remain outside the product
  semantic model. Adapters may inspect them as external inputs, but no product admission
  path treats a provider-specific file wrapper as a trust root. The active optional path
  verifies the provider's exact re-execution input against protected provider-local
  configuration, an exact proof floor, and exact Git bindings before projecting
  `independently_reexecuted`.
- Same-UID multi-agent forgery remains possible in the default (verifier-off) posture. This
  is disclosed, not hidden; it is an OS-level fact, not an ETHOS defect. Operators who need
  the stronger guarantee opt into the lightweight local verifier.

## Proof Or Evidence

- `src/ethos/adapters/mutation/proof.py`, `proof_validation.py`, `proof_artifacts.py`,
  `landing.py`, `accepted.py`, `src/ethos/adapters/repo/git_effects.py`, and
  `src/ethos/adapters/gates/runner.py` — issue and validate the proof closure, keep artifact,
  proof-operation, and Git-effect identity distinct, derive mutation authority outside proof,
  and reject stale HEAD/tree/ref/Lease facts immediately before CAS.
- `tests/unit/kernel/test_proof_plan_binding.py`,
  `tests/unit/cli/test_contracts_land.py`, and
  `tests/unit/adapters/gates/test_runner.py` — pin exact closure, canonical default/full
  floors, artifact variance, DAG identity, Lease-bound candidate authority, pre-transition
  accepted authority, and runner identity drift.
- `src/ethos/adapters/admission/evidence/external.py`,
  `src/ethos/contracts/evidence/external.py` — exact receipt
  contract and provider-local admission boundary.
- `tests/unit/admission/test_independent_verification.py` — exact request/receipt
  binding, protected provider configuration, signature verification, and
  default-off admission behavior without a product-distributed executable.

## Revisit Trigger

Revisit when a hosted forge `pre-receive` is stood up, a provider deploys a local daemon, or
the same-UID threat model changes (for example, agents gain
isolable identities by default). Provider-specific trust-anchor storage, floor allowlists,
latency budgets, and control-plane bootstrap remain local adoption decisions.

## Invariants

- Same-UID local integrity is not an independent anti-forgery boundary.
- Local executed proof claims readiness, not enforcement.
- Stronger assurance requires independent-identity re-execution.
- Offline local operation remains available.
- ETHOS does not bundle an operator's trust anchor.

## Alternatives Considered

| Option | Verdict | Pros | Cons | Decision basis |
| --- | --- | --- | --- | --- |
| Content-addressed local proof plus optional independent re-execution | selected | Keeps local proof deterministic and offline while admitting stronger assurance when configured. | Default local proof cannot prevent a same-UID principal from forging its own environment. | It states the local boundary honestly and permits stronger assurance without making it universal. |
| Add a local MAC or signature under the same UID | rejected | Appears to add cryptographic protection. | The same principal can read the key or modify the verifier; compromise gains a wider blast radius. | It is security theatre under the declared threat model. |
| Require hosted verification for every proof | rejected | Provides an independent execution identity. | Breaks local-first, offline, and multi-worktree operation. | Independent assurance is optional and plane-specific, not the local kernel baseline. |
| Bundle a verifier daemon, key, and deployment recipe | rejected | Improves apparent out-of-box completeness. | Hard-codes operator deployment and trust-anchor choices into product truth. | ETHOS owns the receipt contract, not the verifier deployment. |

## Selected Approach And Rationale

Separate exact local integrity from independent anti-forgery assurance and state
each claim at its real boundary.

## Decision Change Ledger

| Version | Date | Change | Reason | Evidence |
| --- | --- | --- | --- | --- |
| 3 | 2026-07-31 | Defined self-contained proof closure, separated operation and artifact identity, and fixed proof, candidate, accepted, runner, and DAG authority boundaries | Remove historical replay without allowing artifact variance or target bytes to mint authority | Proof, landing, accepted, runner contracts and focused tests |
| 2 | 2026-07-28 | Added explicit rejected assurance models | Make the trust boundary non-negotiable | Terminal-convergence decision discipline |
| 1 | 2026-07-10 | Established local-readiness and independent-verification boundaries | Avoid same-UID security overclaim | Threat-model analysis and proof tests |
