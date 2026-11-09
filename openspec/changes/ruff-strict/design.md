# Design

## Context

Ruff runs with `preview = true` and `explicit-preview-rules = true`
(`.config/checks/ruff/ruff.toml`), so a preview rule applies only by exact code. `noqa` is
forbidden (`ruff --ignore-noqa` and the hygiene test), so every adopted rule is either satisfied or
scoped in the configuration. pytest runs with `--import-mode=importlib`, so test directories need
no `__init__.py`. Two read-only reviews of the rule choices (scratch `catalog-root/ruff-strict/`)
settled the decisions below.

## Goals / Non-Goals

Goals: Ruff reports every bug class it can see in product and tool code, with no rule weakened to
reach zero.

Non-Goals: the shared static gate's floor and adopters' carriers (the gates program's Phase 3);
PLR0402, which `rules/module-layout.md` section 2.5.1 contradicts; PLR2004, PLR0913, PLR0914,
PLR0916, PLC1901, PLW0717, PLR6301, PLR6201, PLR1702 and CPY, rejected with their reasons in the
scratch design; typed records for the signature-repair and status reports, which the gates
program's typed-reports step owns.

## Decisions

1. **Guards.** ERA, T10, TD, FIX, EXE, INT and PYI have no finding today and keep it that way.
2. **Bandit, scoped by evidence.** S603 and S607 are ignored everywhere, so the rules no longer
   review subprocess calls. `tests/` ignores S101, S105, S106, S108 and S314; the conformance
   scripts under `tools/ci/delivery/acceptance/` ignore S101. S105's product hits are names, not
   secrets, and are renamed. Per-file ignores: S314 for the JUnit reports the repository's own
   pytest writes, S606 for the console's `os.execv` into the selected runtime, S202 for the Node
   supply's `extractall(..., filter="data")`, S506 for the two `SafeLoader` subclasses.
3. **Asserts.** The 29 product and tool asserts all narrow a value that an earlier guard
   established. They become `present(value, *gaps)` and `instance(value, kind, *gaps)` in
   `ethos.contracts.outcome`, which raise the same refusal as the guard they replace and which `ty`
   narrows on. Where a type can hold the invariant, it does instead: `NoReturn` on a helper that
   always raises, a block-or-result union in place of a `(block, result)` pair, and a changelog
   release record that keeps a version with its date.
4. **Annotations.** ANN for product and tools with `allow-star-arg-any = true`; `tests/` ignored;
   `Any` stays only for the two Pydantic `Field` factories and the JSON schema bundle (ANN401).
5. **Keyword-only parameters.** PLR0917 for product and tools. The 39 signatures keep their subject
   positional (`root`, `repo` or the selection; the first three where they name what runs, in
   `_run_ready_gate` and `_attestation`) and take the rest by keyword, with every caller.
6. **Preview rules with real findings** are selected by exact code and fixed.
7. **Scoped families.** INP with `tests/` ignored; T20 with `tools/` ignored; ICN with the
   canonical `ElementTree` alias that `rules/module-layout.md` requires.

## Risks / Trade-offs

- With S603 and S607 off, no rule reviews subprocess calls; the process owners and the product
  boundary remain the review.
- Keyword-only conversions change call sites and the test doubles that mirror them; `ty`, the
  impacted sweep and the full proof check them.
