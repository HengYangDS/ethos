# Design

## Context

See [proposal.md](proposal.md). Design revision 5.1 names this Change (`build/runtime/work/architecture-realization/`): `product-architecture.md` lists its tier edge (195), its adopter counterexample (507, row 2) and its research disposition (543, the standard-library `symtable` with `ast`); `restoration-map.md` (118) restores `quality-evidence-admission` task 10.11; `design.md` gives its budget (−100 to +100).

The machine-local receipts are in alphasim, `build/evidence/workflow/closeout/retention/runtime-binding-20261027/`: `gitlab-ci-local-477-pin-prewrite-native-0818.json` (the value refusal, baseline `03fc0661a`) and `claude-adopter-convergence-handoff-5.md`.

Constraints:

- **Budget.** Accepted `dev` has 100 lines of headroom. The product lane agreed that this Change lands after `surface-pruning` (−48) and is measured there; a net above the headroom then splits the Change.
- **History.** `dfc17351c` (2026-10-06) replaced the observer with a 6,000-line flow, effect and custody engine, and `fbc4ae5e9` withdrew it six days later. This design keeps to what the scenarios require.

## Goals / Non-Goals

**Goals:**

- The four accepted scenarios hold, and a spelling-only rewrite leaves observation unchanged.
- The counterexample's value is owned by its real declaration.
- The observer no longer imports the boundary check.

**Non-Goals:**

- Following argv or names through calls, returns or objects. A wrapper's parameter is attributed to its producer, as before.
- Observing a container build's own commands, or `env_file` contents.
- CI `env:` and `variables:` as value owners. No receipt needs them.

## Decisions

### 1. Bindings with positions, not a second parser

One pass over the existing tree records, per scope (module, function, lambda, class), every binding:

- imports, with their aliases;
- assignments and annotated or walrus assignments, with their expression;
- parameters, and definitions;
- `global` and `nonlocal`, which place a binding in the module or the enclosing function.

Each binding holds once its statement completes.

A name read at a site resolves in the innermost scope that binds it, skipping class bodies for nested functions as Python does:

- In the reader's own scope, only bindings before the site count, unless the site is inside a loop.
- From an outer scope, every binding counts, because a function runs after the module.
- An unbound name is a builtin, or a module that a fragment uses without importing it.

One value resolver serves both callees and operands. A callee is a set of qualified names (`subprocess.run`, `os.environ.get`); an operand is a set of strings and literal argv prefixes. So `RUN = subprocess.run; RUN([...])` and `ARGV = (...); run(ARGV)` both resolve.

The standard-library `symtable` was qualified and rejected. It parses the text a second time and cannot take the cached tree. Its table shapes also differ between Python 3.12, 3.13 and 3.14, which add type-parameter and annotation scopes. And it names a scope's symbols without their program positions, which the program-point scenario needs.

### 2. UNKNOWN only for a dynamically chosen sink

`getattr(subprocess, name)` with a computed name makes the carrier UNKNOWN; its static references are still reported. A parameter or a call result passed to a sink invents nothing and keeps the carrier evaluated. Its executable belongs to the caller's literal, which the old engine tried to follow through calls and returns.

Measured on accepted `dev`: 21 of ETHOS's 31 executor calls take a computed argv (`python.as_posix()`, a wrapper's `command`). Marking them UNKNOWN would leave every patch to those files unknown. No governed repository has a dynamic sink lookup.

### 3. Container environment is a native declaration

A Dockerfile carrier (`Dockerfile`, `Containerfile`, `*.Dockerfile`) declares the names of `ENV` (both forms) and `ARG`. A YAML document whose `services` maps to service mappings is a Compose file, and each service's `environment` (mapping or list) declares its names. The Dockerfile joins the text product surface, so the boundary check also reads it.

### 4. The product surface moves to the policy tier

`PRODUCT_SURFACES`, the historical prefixes, the skipped directories, the text names and suffixes, `declared_product_surface_roots` and `product_surface_files` move from `boundary/catalog.py` and `boundary/product.py` to `repository/policy/surfaces.py`. No alias is left. The tier-edge measurement drops from 34 violating edges to 33, with no new edge.

### Spec delta

repository-governance:

- MODIFIED "Python reference observation respects binding and call site": the requirement states the bounded UNKNOWN; the dynamic scenario names a sink chosen by lookup; a new scenario keeps run-time values with their producer.
- ADDED "Container environment declarations own runtime values".

## Risks / Trade-offs

- [A union of reaching values over-approximates] → a branch that assigns an undeclared name is reported. That is the scenario's rule ("a later assignment cannot erase an earlier undeclared input").
- [Removing the name rule loses a consumer] → measured on every governed repository: it only ever produced `python`, `nox` and `pytest`, from constants that nothing ran. Dropping a consumer adds no gap.
- [An adopter gains a true orphan] → `ethos-introduction-film`'s `ffmpeg`, told ahead of the release.
- [Proof time] → the observer takes about 0.4 s more over ETHOS's files.
