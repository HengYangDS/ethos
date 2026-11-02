# Design

## Context

See [proposal.md](proposal.md). `paradigm.toml` declares `[binding] root = ".ethos"` with
`files = ["profile.toml", "release.toml", "rules.toml", "workspace.toml"]`, and `[release]` declares
`version_file` and `changelog`. `RepositoryParadigm` exposes them, and some readers already use
them, for example the parameter resolution's `f"{paradigm.binding.root}/rules.toml"`, which still
restates the file name. The branch roles have no table: `BranchRolePolicy` carries them as dataclass
defaults, and the `repository-paradigm` requirement "Branch roles and Work Lanes use the standard
names" fixes their values.

At `9b124f1e7`, docstrings aside, the restated values are:

| Value                                              | `src/` sites | Owner after this Change        |
| -------------------------------------------------- | ------------ | ------------------------------ |
| a binding carrier path, in a value, gap or message | 55           | `binding_path(role)`           |
| a binding file name, alone or in an f-string       | 16           | `binding_path(role)`           |
| `VERSION`, `CHANGELOG.md`                          | 10           | `paradigm.release`             |
| `candidate/dev`, `work/`, `proposal/`              | 5            | `BranchRolePolicy`, `[branch]` |

`"dev"` also appears three times for other things: a uv dependency group in `adapters/gates/ty.py`
and npm's development dependencies twice in `node_package_supply.py`.

## Goals / Non-Goals

**Goals:**

- Each declared name and carrier path has one source, the paradigm declaration, and every other
  product module builds its values from it.
- A check keeps restated values out of `src/` and lets the recorded `tools/` count only fall.

**Non-Goals:**

- Repository-specific names. Branch roles and binding carriers stay fixed for every repository;
  `declared-parameters` owns the values a repository may change.
- Test fixtures and docstrings. Tests describe what a repository looks like, and docstrings explain
  behaviour to a reader; both may keep literal names.
- Remote names. `[release] clone_remote` and the peer-named remotes already come from the paradigm
  and the release binding.

## Decisions

- **A `[branch]` table.** `release = "main"`, `accepted = "dev"`, `candidate = "candidate/dev"`,
  `work_prefix = "work/"` and `proposal_prefix = "proposal/"`, modelled in
  `contracts/paradigm/declaration.py`. `BranchRolePolicy`'s defaults become factories that read it,
  so a policy built without arguments still carries the standard names. Formation's initial branch
  reads the accepted role. Rejected: a second constant module, which would be a second source.
- **Keyed binding files and one accessor.** `files` becomes a table keyed by role (`profile`,
  `release`, `rules`, `workspace`), and `binding_path(role)` returns `<root>/<file>`. Readers of the
  whole set read the table's values. Rejected: an accessor per file, which makes each new carrier a
  new function.
- **Release carriers read `[release]`.** The `VERSION` and `CHANGELOG.md` sites read
  `paradigm.release.version_file` and `changelog`.
- **Gap codes and messages keep their values.** A gap code or message that names a carrier builds
  the path from `binding_path`, so its text is unchanged and stays tied to the declaration.
- **The check derives its owned set.** An architecture test loads the declaration and reports each
  string constant in `src/` and `tools/`, docstrings aside and outside
  `src/ethos/contracts/paradigm/`, that contains a binding carrier path or a binding file name, or
  equals the version file, the changelog or a multi-segment branch value. Single-word branch names
  are not counted: the same words name unrelated things, and `BranchRolePolicy` is their only
  reader. A new declaration is checked without a new rule.

## Risks / Trade-offs

- [Import cost on the hook path] → The accessor reads the cached declaration that the parameter
  resolution already loads; hook-protocol imports stay lazy.
- [Wrapped call sites grow the product budget] → A path built from the accessor is rarely longer
  than the literal; each touched module is measured before commit.

## Migration Plan

One lane. No value changes, so governed repositories need nothing.
