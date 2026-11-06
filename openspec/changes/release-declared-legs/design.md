# Design

## Context

See [proposal.md](proposal.md). `releaseLegs` in `.config/ci/pipeline.cue` lists the five release
platforms with their runners and Python. The `release-platforms` matrix includes every entry. The
`release-publish` job downloads every uploaded artifact and runs `release_assets.py` over them.

## Goals / Non-Goals

Goals:

- One declaration states which release platforms are required. The workflow and the assembler read
  it and keep no copy.
- A release names every declared platform it does not publish, whether the leg failed or its
  inventories were incomplete.

Non-goals:

- Changing which platforms are required. Windows stays optional.
- Reporting why a leg failed. The leg's job log owns that. The assembler states only that the leg
  produced no qualified artifact.

## Decisions

- **The CUE list is the owner.** `releaseLegs` already names each platform's runner and Python.
  Each entry gains `required: bool`. The release matrix carries `required` into each leg, so
  `continue-on-error` becomes `${{ !matrix.required }}`. The publish step's command line is rendered
  from the same list. Today it passes `--required linux-x64,linux-arm64,macos-arm64` and
  `--optional windows-x64,windows-arm64`.
- **The assembler takes the declaration as input.** `_REQUIRED` goes away. `_HOSTS` stays as the
  set of host names that the runtime naming can produce, and every declared host must be one of
  them. A required host that publishes nothing refuses, as before. A declared optional host without
  an admitted archive is left out. An artifact whose host is not declared refuses, so a stray or
  renamed leg cannot publish.
- **The compiler refuses an impossible declaration.** CUE checks run at every projection:
  - hosts are unique;
  - a required leg is not emulated, because an emulated leg publishes no wheel and cannot stand in
    for a required platform;
  - every journey leg is required.
- **One notes line for every left-out host.** The line names the hosts and states the adopter rule.
  The per-host causes go into `left-out.json`, which the publish job prints.

## Risks / Trade-offs

- A release run dispatched from a main whose workflow predates this Change runs the old assembler
  command. The release jobs check out the tag and only the workflow comes from main, so the
  `--required` and `--optional` arguments and the assembler that reads them ship in the same
  commit.
