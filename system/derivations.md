# ETHOS Derivations

> Design derivations of the Tao axioms (`system/tao.md`). Each is a mechanism that
> eliminates a class of invalid state; none is a root axiom. Product description
> lives in `docs/`; durable machine contracts in `system/*.toml`.

## Five-layer separation

Judgment, contract, method, instrumentation, and proof are separated into distinct
layers (Tao / Contract / Method / Instrumentation / Proof). — from **Form**: keep
the human-trustable and the machine-executable in different representations
(Markdown for judgment, TOML for durable config, JSON for API output).

## First-principle derivations

- **Fail upstream.** Failure blocking moves upstream; the best gate makes an invalid
  action impossible before it mutates tracked truth. — from **Purpose** (shift-left
  is the strongest invalid-state reducer).
- **Provable truth store.** A truth store that cannot be proved or projected safely
  is not a truth store. — from **Trust** + **Purpose**.
- **Checkable generated surface.** A generated surface is a liability unless its
  drift is checkable. — from **Trust**.
- **Derive, don't store.** A workflow state derived from Git, OpenSpec, evidence, and
  contracts beats mutable private state. — from **Purpose** + **Trust**.
- **Tool by total maintenance.** A tool is preferred over hand-written code only when
  it reduces total product maintenance, not merely local effort. — from **Parsimony**.
- **No compatibility residue.** Compatibility residue is a cost center once
  destructive migration is allowed. — from **Parsimony**.

## Kernel-chain principle

One canonical chain, judged from one source and projected once. The concrete
seven-node chain and per-node obligations are architecture, documented in
`docs/architecture/terminal-governance-product-design.md`; the enforced per-node
duty table lives with the schemas and kernel-contract tests. — from **Purpose** +
**Trust** + **Parsimony** (a single source of truth, projected — never duplicated).
