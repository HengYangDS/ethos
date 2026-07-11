---
subject: ethos:decision:proof-trust-boundary
role: decision
state: canonical
relations:
  depends_on: DR-0005
  informs: hosted-enforcement receipt path, local independent-identity verifier adapter
---

# DR-0006: Proof Trust Boundary and Optional Independent-Identity Verification

Status: accepted.

Purpose: fix the honest meaning of a local executed-proof record (a `local_readiness`
claim, not an enforcement guarantee), reject an on-host MAC as security theatre under the
same-UID threat model, and specify the optional, default-off independent-identity
verification plug (lightweight local daemon or hosted forge) as the genuine anti-forgery
trust root.

See also: [Decision Records](../README.md), [Decision Index](../decision-index.md),
and [Accepted Decisions](README.md).

## Record

| Field | Value |
| --- | --- |
| Status | accepted |
| Class | architecture / security |
| Scope | What a local executed-proof record does and does not guarantee; where the genuine anti-forgery trust root lives; the optional verification adapter interface. |
| Supersedes | none |
| Depends on | DR-0005 (declarative runtime spine) |

## Context

ETHOS governs autonomous agents that run as the **same OS user** as the human operator.
The local executed-proof record (`.ethos/state/proof/<head>.json`) is consumed by
`land` / `closeout` / `push` admission to authorize a promotion. Its integrity check
recomputes an **unkeyed sha256** over the record's own body and requires every recorded
run to say `passed`.

Those checks are **self-referential**: the governed agent can author a well-formed record
in which every run says `passed` and compute the sha256 over its own body. So the local
record is **tamper-evident** (it detects partial edits, bit-rot, wrong-HEAD copies,
staleness) but **not tamper-proof** against the very principal ETHOS exists to govern.
An earlier docstring claimed "forgery by file-authoring fails" — that claim was false and
was removed (proof.py, adversarial pin in `tests/unit/mutation/test_proof_forgery_honesty.py`).

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

1. **The local proof record is a `local_readiness` claim, never an enforcement/prevention
   guarantee.** Consumers must not surface a valid local record as "enforced" or
   "prevented". This is now stated in `proof.py`'s docstring and pinned by the forgery
   test. Tamper-evidence (fat-finger / bit-rot / wrong-HEAD / staleness defense) is the
   real and sufficient job of the local layer.

2. **No keyed MAC / signature is added to the local proof record.** Under the same-UID
   threat model it is security theatre and enlarges blast radius. Rejected deliberately.

3. **The genuine anti-forgery trust root is re-execution under an independent identity**,
   expressed through the existing `EnforcementReceipt` / `external_evidence_report` path.
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

5. **The local verifier reference implementation is restricted to the LIGHTWEIGHT path**
   (operator constraint): a single dedicated OS user (e.g. `ethos-verifier`) + one launchd/
   systemd daemon + a private key at `chmod 600` unreadable by the agent user. Agents write
   a request to an inbox they can only append to; the daemon re-executes the pinned,
   out-of-tree ETHOS floor (never the requesting tree's own `ethos` package — the
   judge-is-judged hole) and writes a signed receipt to an agent-readonly path. Per-agent
   containers / per-agent OS users are **out of scope** — one independent verifier identity
   suffices; agents may still share the operator's account.

## Consequences

- ETHOS stops over-claiming: a local land is honestly a readiness assertion. Solo and
  same-UID multi-agent users get exactly that, with no new moving parts.
- The path to a genuine local trust root is specified and ready to *insert* without any
  unused code shipped now (如非必要勿增实体): the plug interface already exists
  (`EnforcementReceipt`); the daemon is a future optional adapter.
- `receipt_digest` in `EnforcementReceipt` is currently regex-validated only (never
  cryptographically verified) and `external_evidence_report` has no `src/` callers. Making
  either load-bearing REQUIRES real signature verification + a pinned out-of-tree issuer +
  an out-of-band floor allowlist + out-of-band trust anchors, and must not be flipped on
  before those exist (else it either DoSes sanctioned promotion or admits forgeries).
- Same-UID multi-agent forgery remains possible in the default (verifier-off) posture. This
  is disclosed, not hidden; it is an OS-level fact, not an ETHOS defect. Operators who need
  the stronger guarantee opt into the lightweight local verifier.

## Proof Or Evidence

- `packages/ethos/src/ethos/adapters/mutation/proof.py` — honest docstring + (a)/(c)
  comments (dev 4086ab81).
- `tests/unit/mutation/test_proof_forgery_honesty.py` — pins that a hand-authored record is
  accepted (forgeable-by-design) and that the docstring does not over-claim; tripwire against
  future over-claiming.
- `packages/ethos/src/ethos/adapters/admission/evidence/external.py`,
  `packages/ethos-core/src/ethos_core/contracts/evidence/external.py` — the plug interface.

## Revisit Trigger

Revisit when any of: (a) an operator opts into the lightweight local verifier (build the
adapter + real signature verification then); (b) a hosted forge `pre-receive` is stood up;
(c) the same-UID threat model changes (e.g. agents gain isolable identities by default).
The five open decisions (server-hook vs SaaS; where trust anchors + floor allowlist live
out-of-band; default posture; re-execution latency/resource budget; control-plane bootstrap)
are settled at that time, not before.
