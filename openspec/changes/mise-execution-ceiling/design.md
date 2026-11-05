# Design

## Context

See [proposal.md](proposal.md).

- **Two environments.** Discovery and resolution run mise in a temporary copy with
  `MISE_CEILING_PATHS` set to the repository's parent. Execution yields
  `_mise_environment(<alias directory>, execution=True)`, whose ceiling is the alias directory's
  parent, the system temporary directory.
- **mise's walk.** mise searches each directory from the working directory upwards for its project
  configuration names, including `.config/mise/config.toml` and `.config/mise/conf.d/*.toml`. At
  the home directory those names are the operator's global files, which mise then loads as project
  configuration. A ceiling stops the walk below the directory it names.

## Goals / Non-Goals

Goals:

- A gate child's mise reads the repository's configuration and nothing above it.

Non-goals:

- Changing resolution, which already stops at the repository's parent.
- Editing or reverting the operator's global configuration.

## Decisions

- **The ceiling is a path list.** mise reads `MISE_CEILING_PATHS` with Rust's
  `std::env::split_paths`, in `src/env.rs` of both v2026.10.25 and v2026.11.2. That splits on `:`
  on Unix and `;` on Windows, which is Python's `os.pathsep`. The execution value joins the alias
  directory's parent, kept for children that run from a temporary directory, with the resolved
  repository root's parent.
- **A native regression.** The test puts the repository under a fixture home whose global
  configuration declares another tool. A gate child's `mise ls --current --json`, run through the
  same helper that runs admitted commands, must list only the repository's declared tool. It runs
  the real mise, like the other boundary tests.

## Risks / Trade-offs

- A repository that relied on inheriting an ancestor's mise configuration stops seeing it during
  execution. Resolution never admitted such configuration, so a gate that relied on it was already
  running unresolved tools.
