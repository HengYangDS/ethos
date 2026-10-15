## Why

ETHOS governs thirteen repositories, ETHOS included. They already agree on a few things:

- the `.ethos/profile.toml` binding;
- the OpenSpec layout;
- SSH-signed Conventional Commits;
- the ignored `build/` root.

Beyond that, each repository encodes the same concerns in its own way:

- seven `.ethos/` file sets;
- five commit-subject grammars;
- four decision-record namings;
- three `.config/` taxonomies;
- tool configuration scattered across the root and package manifests;
- orchestration through native tasks in some repositories and shell scripts in others;
- hand-maintained CI files for several Forges.

ETHOS documents currently forbid making repository layout universal, so the drift has no owner. The repositories' owner has directed that every ETHOS-managed repository, ETHOS itself included, follow one top-down paradigm. That paradigm contains only what the repositories genuinely share.

## What Changes

- Define one repository paradigm owned by ETHOS. It has two layers:
  - a universal core for every governed repository;
  - ecosystem modules for Python, Node and Go repositories. Each module holds only what every repository of that ecosystem shares.

  Domain and product layout stays with each repository: source trees, content, media, test organization and provider shape.

- Core obligations:
  - The root carries only a closed catalog of protocol entries.
  - Tool configuration lives under `.config/`, grouped by consuming tool and using each tool's native basename. It uses TOML when the tool reads TOML and is always passed explicitly; there are no root pointer files.
  - `.config/` holds only configuration that a tool or repository check consumes.
  - The `.ethos/` binding uses only ETHOS-defined files.
  - Commits follow one Conventional Commit grammar with SSH signing.
  - Branch roles use the standard names.
  - Released products keep Keep a Changelog and `VERSION`.
  - Documents use YAML front matter, and decision records are named `dr-NNNN-<topic>.md`.
  - Markdown and YAML are formatted by Prettier and TOML by taplo. `.editorconfig` and `.gitattributes` are present.
  - One locked toolchain owner exposes the `bootstrap`, `fix` and `check` verbs.
  - Orchestration runs through native commands and toolchain-owner tasks on every supported platform. The only tracked scripts are official generator output.
  - CI that targets several Forges is defined once in `.config/ci/` and projected.
  - Repository-authored names are lowercase kebab-case.
- Enforce the paradigm in the same way for every repository:
  - The repository audit gains a paradigm report that blocks prove, land and publish.
  - Prewrite refuses a new path that the paradigm rejects.
  - Pre-commit hooks read secret-scanning and Ruff configuration from canonical `.config/` paths, so moving those files keeps the checks effective.
- **BREAKING** for adopters: a repository that does not conform fails proof once it runs a runtime carrying this Change. Each repository migrates through its own Change, and the migration and the runtime switch land in the same batch.
- Amend the Product Design Contract, the Config Boundary Model and the Repository Profile Contract where they forbid a common repository layout. Record the reversal and its limits in DR-0012. ETHOS conforms itself in this Change.
- Out of scope:
  - product and domain layout, test organization and documentation subject layout (DR-0011 stands);
  - Forge-side settings;
  - migration of the alphasim and di-effect families, which their own later Changes own.

## Capabilities

### New Capabilities

- `repository-paradigm`: the common repository contract for governed repositories and its uniform conformance verdict. It covers the root protocol catalog, the configuration plane, the binding file set, process conventions, formatting and naming.

### Modified Capabilities

None.

## Impact

Affected areas:

- the repository audit composition, prewrite admission and pre-commit admission;
- a packaged paradigm contract next to the generated-artifact topology contract;
- greenfield formation, which consumes the contract;
- three governance documents and one decision record;
- ETHOS's own root, `.config/`, `.ethos/`, CI scripts, Markdown formatting and file names.

Every adopter must migrate before it switches runtime. No new command, lifecycle, registry or per-repository exception list is introduced.
