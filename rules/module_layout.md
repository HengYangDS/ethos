# Module Layout And Visibility Rules

This document is the SSOT for how ETHOS Python code is organized — physically
(directories/files) and logically (public vs private surface). It exists because
organization is a correctness property, not a matter of taste: a reader or a tool
must be able to tell, from name and place alone, what a symbol is for and whether
it may be depended upon.

Derived from the parsimony axiom in `system/axioms.md` and the
general module-layout boundary study and `system/axioms.md`.

| Field | Rule |
| --- | --- |
| Authority | [Product Design Contract](../docs/governance/product-design-contract.md), `system/axioms.md`, `.config/checks/module-layout/policy.toml` |
| Trigger | Creating, moving, renaming, splitting, importing, or deleting repository-owned Python. |
| Action | Model one narrow concept per owner, preserve carrier-native syntax, and choose absorb, precise rename, semantic split, or delete for mixed ownership. |
| Evidence | `tools/ci/scripts/run-module-layout.sh` and focused contract tests. |
| Stop | Ambiguous ownership, duplicate command owners, facades, private cross-module imports, or a split justified only by a metric. |

## 1. Physical organization — semantic boundaries, not metric shapes

- A package is a **deploy unit** (versioned, released). Its boundary is dependency
  direction, not theme.
- A module directory is a **semantic axis**. When a directory accumulates modules,
  group them into sub-packages only when the group owns a distinct concept,
  invariant, authority, or change reason. Directory width and file count are
  observations, never automatic split authority.
- A module name states one narrow domain concept or role slice (`transition.py`,
  `measurement.py`, `report.py`). Generic entry names are not a default.
- Native carrier syntax remains native: pytest discovery names such as
  `test_*.py` and descriptive tool scripts such as `release_supply_chain.py` are
  not product package topology. The same semantic invariants apply, but a naming
  convention required by the carrier is not itself a violation.

### 1.1 Semantic and physical isomorphism

Physical structure follows actual semantics, not line-count targets or inherited
folder shape. Every governed module MUST have:

1. one explicit, narrow concept;
2. one authoritative truth or effect owner;
3. one primary reason to change;
4. inputs and outputs that do not silently claim another module's authority; and
5. a path whose words state that concept and role.

`core.py`, `common.py`, `shared.py`, `utils.py`, `helpers.py`, `misc.py`,
`base.py`, `manager.py`, and `service.py` do not identify a narrow concept and
are blocked without exception. A genuine kernel, report, registry, transition,
adapter, or aggregator uses that exact semantic name. Configuration cannot
exempt an ambiguous path, and a baseline cannot normalize it.

An ambiguous or mixed module has exactly one terminal disposition:

- **absorb** it into the existing authority;
- **rename** it to its precise concept;
- **split** it along distinct truth owners or independent change reasons; or
- **delete** it when it carries no unique semantics.

Splitting to game ELOC, moving the same mixture under several files, or retaining
the old path as a facade is not remediation. "As few entities as necessary"
means few semantic entities, not few files.

Command ownership follows the same rule. Concrete Cyclopts declarations own CLI
names, parameters, help, and dispatch; `system/gates.toml` owns only proof-gate
adapters. A `surface/cli/**/core.py` command owner, or one module that owns more
than one Cyclopts application, is a hard layout defect.

## 2. Logical organization — public vs private

### Modules

- **Public module**: name without a leading underscore. It may be imported across
  package boundaries and is part of the package's contract.
- **Private module**: name with a leading underscore (`_parser.py`, `_encoding.py`).
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
  `from ethos.domain.plan import matching_rule_gates`, not a re-export shell.
- Package-root `__init__.py` files stay declaration-only (a docstring). No
  re-export barrels, no `__all__` piled with forwarded names, no alias shims
  (`from x import y as main`). Compatibility residue is a cost center.
- Ordinary modules must not become compatibility facades either. A module that
  only imports/re-exports names and optionally declares `__all__` is stale
  surface; a module-level `__getattr__` that dynamically forwards exports is the
  same violation in lazy form. Move callers to the concrete defining module and
  delete the shell.
- One import per line (ruff isort `force-single-line`); absolute imports only
  (ruff `TID`). Runtime-only type imports go under `if TYPE_CHECKING:` — EXCEPT
  cyclopts command signatures, whose annotation types must stay runtime imports.

## 2.5 Import rules (explicit)

These are the enumerated, enforced import rules. A dependency edge is a claim about
architecture; these rules make the claim honest and checkable.

1. **Direction (import-linter, enforced):** the pure kernel never imports the
   product. `ethos` and `ethos_contracts` are pure leaves — they import NO
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
8. **No import-only compatibility modules:** do not preserve old import paths by
   turning `core.py`, `foo.py`, or any ordinary module into a re-export shell.
   Concrete defining modules are the migration target.

### 2.5.1 `import` vs `from ... import`, and when to use `as`

- **Default: `from package.module import symbol`.** Use a symbol directly; this is
  the common case and reads cleanest.
- **`import package.module` (bind the module) only when** you genuinely want the
  module namespace at the call site — usually to disambiguate several same-named
  functions, or when the module name itself carries meaning (`ethos.adapters.git`
  called as `git.current_head(...)`). Prefer the shortest honest name.
- **Do NOT bind submodules through a package root** (`from package import module`).
  If the call site genuinely needs a module namespace, import the concrete
  module (`import package.module as module_name`); otherwise import the concrete
  symbol from the defining module.
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

The single effective-LOC limit for each carrier role lives in
`.ethos/rules.toml [quality.code_size]` and is enforced by the code-size gate.
There is no soft/hard split and no per-file exemption. A breach requires semantic
review, but only a distinct concept, invariant, authority, or reason to change can
justify a split; otherwise the module is simplified or absorbed.

## 4. Why this matters

A symbol's name and location are a contract. `_x` says "do not depend on me";
`foo/report.py` says "the reporting slice of foo". When names and places are
honest, humans recover intent by reading and tools enforce boundaries mechanically
— which is the whole point of a governance runtime.
