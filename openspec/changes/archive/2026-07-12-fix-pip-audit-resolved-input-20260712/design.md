## Context

The existing owner script already derives its audit input from a frozen `uv
export`, so dependency resolution is complete before `pip-audit` starts.  The
default `pip-audit` requirement flow nevertheless creates a temporary virtual
environment and upgrades packaging tools.  That bootstrap is unrelated to the
declared audit input and fails when package-index access is unavailable.

## Design

The owner script will pass `--no-deps --disable-pip` to `pip-audit` after
writing the exported requirements file.  `--no-deps` declares that the fully
pinned exported set needs no further resolver pass; `--disable-pip` prevents
the compatible pip bootstrap path.  The script continues to query the
vulnerability service, emits the same raw JSON and summary envelope, and fails
on vulnerabilities or audit-service failures.

## Alternatives

- Keep default `pip-audit` resolution: rejected because it upgrades packaging
  tools in a temporary environment before auditing the declared input.
- Use `--no-deps` alone: rejected by measurement because `pip-audit` still
  attempted the temporary pip upgrade.
- Rely on a host package cache: rejected because it hides the input-bound gate
  behind mutable workstation state.

## Proof Strategy

Run the focused architecture test, the owner script, OpenSpec strict
validation/lifecycle checks, and a HEAD-bound executed proof.  The regression
test asserts both flags and verifies the emitted evidence envelope.
