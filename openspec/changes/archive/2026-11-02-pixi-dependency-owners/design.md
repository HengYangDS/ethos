# Design

## Context

See [proposal.md](proposal.md). The Mise rule reads `[tools]` from `.config/mise/config.toml` and
adds each tool's `rename_exe` or the last segment of its identity. No install layout is read, so a
verdict never depends on the auditing host. Pixi records each installed package's files in
`.pixi/envs/<env>/conda-meta/<package>.json` (`pip` installs `bin/pip` and `bin/pip3`), but those
records exist only after `pixi install` on the auditing host.

## Goals / Non-Goals

**Goals:**

- A repository that declares a conda package in its Pixi manifest may document and run that package's
  own command.
- The verdict is a function of tracked declarations only.

**Non-Goals:**

- Reading `conda-meta` install records or other executables of a package.
- Owning PyPI dependencies, which name distributions, not executables, or host installers such as
  Homebrew, which no repository toolchain declares.

## Decisions

- **The package name is its executable, as a Mise tool's last segment is.** It is exact for the case
  that motivates the Change (`pip`), and it reads no host state. A package whose command differs
  from its name stays refused until its repository declares the command in another owner.
- **`pixi.toml` takes precedence over `[tool.pixi]`, as Pixi itself does** when both exist in one
  directory.
- **Malformed manifests own nothing**, as a malformed Mise configuration owns nothing.

## Risks / Trade-offs

- [A package name over-owns a phantom executable] → Nothing runs a phantom; companion executables
  stay refused.
- [A conda package name differs from its command] → It stays refused and is reported, which is the
  current behavior.
