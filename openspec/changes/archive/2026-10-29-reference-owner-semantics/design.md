# Design

## Context

See [proposal.md](proposal.md). Product-reference closure is enforced in two places:

- **Prewrite patch admission** runs in every governed repository. It checks the changed carriers
  against owners compiled from the baseline commit and the root's installed environment.
- **The semantic closure** runs only in ETHOS's own product audit.

Adopters therefore meet reference ownership only when they edit a file. Every false owner or
false observation in the shared reference modules then becomes a refusal at that moment.

## Goals / Non-Goals

**Goals:**

- Each observed identity takes its kind from the native construct that produced it. Commands,
  executables, Python application variables and domain terms stay distinct.
- First-party and installed-module ownership follows the repository's own tree and its native
  environment managers.
- One admission names every reference that a repository has not declared.
- Product code shrinks within its 70,000-line ceiling.

**Non-Goals:**

These are follow-ups owned by this repository's lane owner. The next action for each is a design
for committee review after `0.2.0-alpha.20`, reviewed by 2026-11-02.

- **CI step shells.**
  - The step's language comes from its native declaration: GitHub `shell`, `defaults.run.shell` or
    the runner OS, and for GitLab a runner record's shell matched by job tags after `extends`.
  - PowerShell cmdlets are owned by the shell.
  - Until then, Windows setup steps are kept as retained `operating-system-glue`, and no new
    cmdlet runner record is added.
- **Shell grammar:** multi-line `$(…)`, `$((…))` arithmetic, `<placeholder>` text read as a
  redirection, and script-directory import roots such as `.githooks`.
- **Toolchain executables.** An exact owner for the executables that a tool declared in the locked
  Mise toolchain provides. A name inferred from a tool spec is not authority: `rust` provides
  `rustup`, and `aqua:cli/cli` provides `gh`.
- **Command identities bound by console scripts**, for example `dmgr = "dmgr_cli.main:app"`.
- **Adopter closure at proof**, decided with each adopter owner on a post-release survey.

## Decisions

- **Command identities come only from authored Cyclopts names** (`python_syntax.py`).
  - An App's name is its literal `name=`. Without one, the App has no static name, and every App
    registered under it has none either.
  - A `.command` decorator contributes an identity only when its owner variable resolves to a
    Cyclopts App with a fully named path. A decorator owned by another framework, such as Typer,
    contributes nothing, and neither does a non-literal `name=`.
  - A function without a literal name takes `cyclopts.default_name_transform` of its own name,
    which is the name Cyclopts serves.
  - Three heuristics are deleted:
    - the variable-name fallback;
    - the cross-module guess that matches by variable name;
    - the `App(` text prefilter, which missed modules that only register Apps.
  - ETHOS's own Apps all carry literal names, so its command identities are unchanged.
  - Adopter identities that rested on variable names disappear. They never matched what users
    type, so no refusal appears.
- **A bare word in prose is a term** (`markdown.py`).
  - Inline code outside OpenSpec scenarios that holds a single token and no prompt records
    nothing.
  - Multi-token inline code keeps the existing match against the declared vocabulary, so a
    declared root followed by an undeclared subcommand is still refused.
  - The broader invocation classifier would hide that refusal and is not used here.
- **Package-relative imports stay internal** (`_Bindings.bound`).
  - An `ImportFrom` with `level > 0` adds no top-level import.
  - Its bindings are qualified relative to their package, so `from .subprocess import run` is not
    the standard-library sink.
- **First-party modules come from the repository tree** (`declarations._python_import_owners`).
  - Each tracked `.py` carrier owns its first path component and the head of its module name,
    which covers the repository root and a leading `src/`.
  - The literal module exceptions in `closure.py` are deleted.
  - The governed binding owns the product's import package. A governed repository may run
    `python -m ethos.cli`, as it may run the product's scripts.
  - Nested `src` roots and build-backend declarations would give the same results on every
    governed repository today, so neither is needed.
- **Pixi environments for prewrite** (`observation.installed_distribution_modules`).
  - The distribution map reads site-packages under `.venv` and under each `.pixi/envs/*`
    environment.
  - It still maps only distributions that the baseline declares.
  - The ETHOS-only closure reads no environment; it needs none.
- **Every refusal is reported.**
  - Patch admission returns the complete ordered list of reference and effect gaps, and its first
    entry remains the reason.
  - Prewrite's required gaps include all of them.
- **One parse rule and one computation.**
  - The line-fragment fallback `python_trees` is deleted. Owners and observations use
    `complete_python_tree`, which ignores syntax warnings instead of failing on them.
  - `product_references_from_files` takes command owners from `command_owner_sources_from_files`.
  - The dead `before` set in `native_owned_references_from_files` is removed.

## Risks / Trade-offs

- **[Adopter command identities disappear]** → Prose that names a real adopter command is not
  checked until console scripts bind commands. The old identities used variable names that users
  never type, so no real coverage is lost.
- **[A first-party name coincides with a third-party module]** → The repository owns the name only
  when its own root or `src/` provides it. That is the resolution Python performs.
- **[Host-local environment]** → The map is read fresh at each admission, as `.venv` already is.
  It cannot admit an undeclared distribution.
- **[Adopter patches still meet true gaps]**
  - Complete refusal lists can be longer than the first reason an adopter saw before.
  - Examples are runner executables, runtime inputs and pipeline-installed tools that the
    repository never declared.
  - Each must be declared in the baseline before the patch that uses it: in the runner record, in
    the runtime surface, or as a gate command.
