# Proposal

## Why

Governed repositories meet ETHOS's product-reference closure only at prewrite, where a changed
carrier must reference only identities that its baseline owns. Adopters report false refusals
there. di-effect's prepared Gitleaks and Taplo migrations stop at `import:yaml` and
`executable:app`. A read-only survey of twelve governed roots finds 418 latent refusals that
editing the consuming file would surface; ETHOS's own control is 0.

Five causes in the shared observation account for most of them:

- A Cyclopts application's variable name becomes a command. As a result, a MySQL user named
  `app` in prose reads as an executable.
- A package-relative import becomes a top-level import.
- Distributions map to modules only through `.venv`, not pixi environments.
- The repository's own modules are first-party only through a declared list plus a literal
  `ethos`, `tests`, `tools` exception.
- Prewrite reports only the first refusal, so an adopter learns its gaps one at a time.

## What Changes

- **Command identities come from authored command declarations.**
  - A Cyclopts App names a command only through its literal `name`, and its commands get
    identities only under a fully named path.
  - A variable name, a non-literal name and a decorator that no named App owns declare nothing.
  - Names derived from function names follow Cyclopts' own transform.
  - A single bare word in prose is a term, not an invocation.
- **Package-relative imports stay inside their package.** They add no top-level import and bind
  no standard-library sink.
- **The repository's own tree owns its first-party modules.**
  - A module at the repository root, or under a leading `src/`, is first-party.
  - The literal exception list is removed.
  - The product binding owns the product's import package, as it already owns the product's
    scripts.
- **Pixi environments map declared distributions for prewrite**, as `.venv` does.
- **Prewrite reports every refused reference** in a patch, not only the first.
- **One parse rule and one command-owner computation.**
  - Owners come from complete syntax trees only; the line-fragment fallback is deleted.
  - A syntax warning no longer makes a valid file unparseable.
- **CHANGELOG.** One entry under `[Unreleased]`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`:
  - command identities come from authored command declarations;
  - the repository's own tree owns its first-party modules;
  - installed environment metadata maps only declared distributions;
  - patch admission reports every refused reference.

## Impact

- **Product code.** Python product code shrinks; `design.md` records the measurement against the
  70,000-line ceiling.
- **Governed repositories.**
  - The false refusals of these classes disappear, and the projection gains no refusal for any
    root.
  - Adopter command identities that were derived from variable names disappear. They never
    matched what users type.
  - True gaps remain, such as CI-runner executables that an adopter never declared. They are now
    reported together.
- **Follow-ups outside this Change:**
  - PowerShell and other CI step shells;
  - shell substitution and placeholder grammar;
  - executables declared by a toolchain;
  - command identities bound by console scripts;
  - adopter closure at proof.
