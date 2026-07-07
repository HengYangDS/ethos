# Module Layout And Visibility Rules

This document is the SSOT for how ETHOS Python code is organized — physically
(directories/files) and logically (public vs private surface). It exists because
organization is a correctness property, not a matter of taste: a reader or a tool
must be able to tell, from name and place alone, what a symbol is for and whether
it may be depended upon.

Derived from the parsimony axiom in `system/axioms.md` and the
di-effect module-layout study (`.ethos/quality-regime-decision.md` §3).

---

## 1. Physical organization — semantic sub-packages, never suffix-flat

- A package is a **deploy unit** (versioned, released). Its boundary is dependency
  direction, not theme.
- A module directory is a **semantic axis**. When a directory accumulates modules,
  group them into sub-packages by MEANING, not by a shared name suffix.
- **Flat-directory limit**: no more than **8** governed `*.py` modules at one
  directory level (excluding `__init__.py`). Beyond that, introduce semantic
  sub-packages. (Borrowed from di-effect's flat_directories trigger.)
- **Anti-pattern — suffix-flat**: `foo_report.py`, `foo_native.py`, `foo_index.py`
  side by side is forbidden as steady state. Prefer `foo/report.py`,
  `foo/native.py`, `foo/index.py` — a `foo/` sub-package with a semantic interior.
- The canonical entry module of a sub-package is `<pkg>/core.py` (or the concept
  name); siblings are named by their role slice (`normalize.py`, `report.py`).

## 2. Logical organization — public vs private

### Modules

- **Public module**: name without a leading underscore. It may be imported across
  package boundaries and is part of the package's contract.
- **Private module**: name with a leading underscore (`_base.py`, `_shared.py`).
  It is an implementation detail of its own package and MUST NOT be imported across
  package boundaries.

### Functions and classes

- **Public function/class**: name without a leading underscore. It is callable by
  other modules. Public definitions carry a docstring (the ruff `D` gate enforces
  this).
- **Private function/class**: name with a leading underscore (`_helper`). It is an
  implementation detail of its own module. Other modules MUST NOT call it; if a
  private helper is needed elsewhere, promote it (rename without underscore) or move
  it to the right layer — do not reach into another module's privates. (The ruff
  `SLF` gate flags cross-module private access.)

### Import discipline

- Import concrete submodules, never through package-root facades:
  `from ethos.domain.plan import graph_for_paths`, not a re-export shell.
- Package-root `__init__.py` files stay declaration-only (a docstring). No
  re-export barrels, no `__all__` piled with forwarded names, no alias shims
  (`from x import y as main`). Compatibility residue is a cost center.
- One import per line (ruff isort `force-single-line`); absolute imports only
  (ruff `TID`). Runtime-only type imports go under `if TYPE_CHECKING:` — EXCEPT
  cyclopts command signatures, whose annotation types must stay runtime imports.

## 2.5 Import rules (explicit)

These are the enumerated, enforced import rules. A dependency edge is a claim about
architecture; these rules make the claim honest and checkable.

1. **Direction (import-linter, enforced):** the pure kernel never imports the
   product. `ethos_core` and `ethos_contracts` are pure leaves — they import NO
   other ethos package. Every other package may import only DOWNWARD
   (surface → domain → adapters → repository/quality/assistants → contracts/core).
   The wrong direction is a hard CI failure. Contracts in
   `.config/checks/import-linter/contracts.ini`.
2. **Absolute only (ruff TID):** no relative imports (`from .x import y`). Every
   import names its full package path, so grep and move are reliable.
3. **One symbol per line (ruff isort force-single-line):** `from m import a` then
   `from m import b`, never `from m import a, b`. Line-addressable import churn.
4. **Concrete submodule, not root facade:** import from the module that DEFINES the
   symbol, never a package-root re-export. Package roots export nothing.
5. **No cross-package private import:** never import another package's `_private`
   module or `_helper` (ruff SLF flags private access). Depend on public surface;
   if you need a private, it is mis-placed — promote or relocate it.
6. **Deferred/typing imports:** type-only imports belong under `if TYPE_CHECKING:`
   (ruff TC). The one exception is a cyclopts command signature, where the
   annotation type (`Path`, etc.) must be a runtime import so cyclopts can bind the
   argument — mark it `# noqa: TC003` with that reason.
7. **Lazy heavy imports at the surface:** a command-group module
   (`surface/cli/<group>.py`) imports only the domain/adapter deps ITS commands
   need, so a group's heavy dependencies load only when that group is imported —
   keeping common commands fast. This is why command bodies live in group modules,
   not one monolith.

### 2.5.1 `import` vs `from ... import`, and when to use `as`

- **Default: `from package.module import symbol`.** Use a symbol directly; this is
  the common case and reads cleanest.
- **`import package.module` (bind the module) only when** you genuinely want the
  module namespace at the call site — usually to disambiguate several same-named
  functions, or when the module name itself carries meaning (`ethos.adapters.git`
  called as `git.current_head(...)`). Prefer the shortest honest name.
- **`as` is for necessity, not cosmetics.** Use `as` ONLY when:
  1. two imported names genuinely collide, or
  2. a module is bound as a namespace and its dotted path is too long to repeat
     (`import ethos_repository.repository_audit as repository_audit_module`).
- **Do NOT use `as` to add a `_` prefix** (`emit as _emit`, `resolve_root as
  _root`). That is compatibility residue — it exists only to preserve old
  call sites. Use the real public name (`emit`, `resolve_root`) and update callers.
  A leading `_` marks a definition private in ITS OWN module; it is not an import
  decoration.
- **Do NOT rename canonical symbols** via `as` (`from x import run_y as main`,
  `MapBackend as PMap`). Canonical names are part of the contract (AGENTS.md).

## 3. Size and split

Per-role effective-LOC limits and split-by-surface triggers live in
`.ethos/rules.toml [quality.code_size]` and are enforced by the code-size gate:

- logic modules: soft 400 / hard 600
- surface (CLI command groups): soft 800
- global hard ceiling: 1200 (no role buys unbounded growth)
- split trigger: a module past its soft limit, or with too many public
  functions/classes, is decomposed into a semantic sub-package.

## 4. Why this matters

A symbol's name and location are a contract. `_x` says "do not depend on me";
`foo/report.py` says "the reporting slice of foo". When names and places are
honest, humans recover intent by reading and tools enforce boundaries mechanically
— which is the whole point of a governance runtime.
