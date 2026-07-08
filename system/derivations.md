# ETHOS Derivations

> Design derivations of the derived axioms (`system/axioms.md`). Each mechanism
> eliminates a class of invalid state. Product description lives in `docs/`;
> durable machine contracts live in `system/*.toml`.

## Five-layer separation

Judgment, contract, method, instrumentation, and proof are separated into
stable layers: Axioms / Contract / Method / Instrumentation / Proof.

This follows **Authority before surface** and **Boundary before adapter**:
Markdown carries human judgment, TOML carries durable config, JSON carries
machine output, and provider files project the repository-owned contract instead
of owning product semantics.

## First-order derivations

- **Fail upstream.** Failure blocking moves upstream; the strongest gate makes an
  invalid action impossible before it mutates tracked truth. This follows
  **Signal before disorder** and **Evidence before claim**.
- **Provable truth store.** A store that cannot be proved or projected safely is
  not a trustworthy store. This follows **Evidence before claim**.
- **Checkable generated surface.** A generated surface is a liability unless its
  drift is checkable. This follows **Authority before surface**.
- **Derive, do not duplicate.** Workflow state derived from Git, OpenSpec,
  evidence, and contracts is stronger than mutable private state. This follows
  **Authority before surface** and **Parsimony before expansion**.
- **Tool by total maintenance.** A tool is preferred over hand-written code only
  when it reduces total product maintenance, not merely local effort. This
  follows **Parsimony before expansion**.
- **No compatibility residue.** Compatibility residue is a cost center once
  destructive migration is allowed. This follows **Parsimony before expansion**.

## Kernel-chain principle

One canonical chain, judged from one source and projected once. The seven-node
chain and per-node obligations are architecture, documented in
`docs/plans/terminal-governance-product-design.md`; enforced per-node
checks live with schemas and kernel-contract tests. This follows **Authority
before surface**, **Evidence before claim**, and **Parsimony before expansion**.
