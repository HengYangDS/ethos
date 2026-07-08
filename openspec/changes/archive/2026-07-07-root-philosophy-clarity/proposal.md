## Why

The repository currently treats `问道` too much like an operational subsystem:
the derived axiom file name, low-level comments, and tests encourage agents to cite philosophy labels or
numbered first principles in implementation and configuration files. That weakens
信达雅: the root text becomes less faithful to its role, less clear as a product
constraint, and less elegant through slogan-like reuse.

## What Changes

- Keep `问道` as the canonical root text in the Product Design Contract.
- Rename the machine-adjacent derived reading to `system/axioms.md`.
- Rewrite root interpretation docs so the kernel is an engineering compression,
  not a translation or feature map of the verse.
- Remove philosophy labels from active low-level implementation, hook, and config
  surfaces; those files state concrete engineering invariants instead.
- Add architecture tests that prevent root-text duplication and slogan-like
  implementation comments from returning.

## Capabilities

- `kernel`: subject=root-philosophy-clarity; reuse=reuse; change=rename; facet:lifecycle=authoring; facet:surface=docs; facet:authority=docs
- `kernel`: subject=root-philosophy-clarity; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=test; facet:authority=test

## Out Of Scope

- No runtime command behavior changes.
- No new philosophical subsystem or product ontology.
- No rewrite of archived evidence or archived OpenSpec history.
- No philosophical-subsystem rename of kernel objects such as Authority, Evidence, Claim, or Chronicle.
