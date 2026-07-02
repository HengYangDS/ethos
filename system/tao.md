# system/tao.md
# Human source for value judgment and compression — the Tao layer of the
# five-layer kernel (Tao / Contract / Method / Instrumentation / Proof).
#
# This file holds aesthetic and value judgment: what is worth preserving,
# simplifying, or rejecting. It is human-authored Markdown, not machine state.
# Long design belongs in docs/; durable machine contracts belong in system/*.toml.

## Product Thesis

ETHOS is a repository governance product. Quality is one governed view of the
product, not the product itself. ETHOS governs one Git repository through one
loop: `status -> plan -> prove -> land -> publish`.

The answer must be small enough for humans to trust and structured enough for
machines to execute. ETHOS therefore separates judgment, contract, method,
instrumentation, and proof.

## Writing Standard

| Standard | Meaning | Consequence |
| --- | --- | --- |
| Trustworthy | No claim without authority or proof. | Evidence and citations bind claims. |
| Expressive | Humans and machines can recover intent. | Markdown for judgment, TOML for durable config, JSON for API output. |
| Elegant | No excess surface. | Delete parallel entities, wrappers, and historical residue. |

## First Principles

1. A repository governance product is useful only when it reduces invalid states.
2. Failure blocking must move upstream. The best gate makes an invalid action
   impossible before it mutates tracked truth.
3. A truth store that cannot be proved or projected safely is not a truth store.
4. A generated surface is a liability unless drift is checkable.
5. A workflow state stored as mutable private state is weaker than a state
   derived from Git, OpenSpec, evidence, and contracts.
6. A new entity is justified only when it owns a distinct semantic obligation.
7. A tool is preferred over hand-written code only when it reduces total product
   maintenance, not merely local implementation effort.
8. Compatibility residue is a cost center after destructive migration is allowed.

## Kernel Chain

The single canonical chain, judged from one source and projected once:

```
JudgmentSource -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle
```

JudgmentSource is the authority for decisions. Change owns lifecycle. Claim binds
evidence but does not own lifecycle state and must not assert semantic truth
unless a semantic verifier checked it. Chronicle records judged history.

See also: docs/architecture/terminal-governance-product-design.md (target design),
docs/governance/product-design-contract.md (product contract).
