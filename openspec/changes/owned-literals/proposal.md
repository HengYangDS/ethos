# Proposal

## Why

The paradigm declares the names and carrier paths that every governed repository shares, yet product
code restates them as string literals, so the declaration is not the source of the values it names
and a literal can drift from it without any check noticing.

- At `9b124f1e7`, `src/` restates them in 86 string constants across 37 modules, docstrings aside:
  55 contain a binding carrier path such as `.ethos/release.toml`, gap codes like
  `repository_profile_invalid:.ethos/profile.toml` among them; 16 name a binding file, such as
  `"rules.toml"` or the `/release.toml` of an f-string; 10 are `VERSION` or `CHANGELOG.md`; 5 are
  the branch values `candidate/dev`, `work/` or `proposal/`. `tools/` holds 19 more in 8 modules.
- `paradigm.toml` declares `[binding] root` and `files` and `[release] version_file` and
  `changelog`, and a few readers already build paths from them, but no table declares the branch
  roles: `BranchRolePolicy` (`src/ethos/contracts/branch/roles.py`) holds `main`, `dev`,
  `candidate/dev`, `work/` and `proposal/` as dataclass defaults.
- On 2026-11-01 the owner asked that ETHOS remove hard-coding globally in favour of configuration.
  `declared-parameters` made the tunable values declared parameters and left names and carrier paths
  to this Change. They are fixed for every repository, so this Change reuses the declaration but not
  the override rule.

## What Changes

- The paradigm declares the branch roles in a `[branch]` table and keys the binding files by role.
- `BranchRolePolicy` takes its defaults from the declaration, and product code builds every binding
  carrier path, binding file name, version source, changelog and branch value from the declaration,
  including the gap codes and messages that name a carrier, whose values stay the same.
- An architecture check derives the owned values from the declaration and reports a string constant
  that restates one in `src/` or `tools/`. It is 0 for `src/` when this Change lands, and the
  recorded `tools/` count only falls.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: the paradigm declares the branch roles, and product code reads every
  declared name and carrier path from the declaration.

## Impact

`src/ethos/contracts/paradigm/paradigm.toml` and its model, `src/ethos/contracts/branch/roles.py`,
the 37 modules that restate a declared value, one architecture test and the `repository-paradigm`
specification. Governed repositories see no change: every value, gap code and message stays the
same, and a repository still cannot rename a branch role or a binding carrier.
