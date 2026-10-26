# Design

## Context

See [proposal.md](proposal.md). The accepted `dev` carries every fix that the entry describes. GitLab
cannot be reached while the owner is off the intranet.

## Goals / Non-Goals

**Goals:**

- One release that carries every accepted fix, so each adopter rebinds once.
- A changelog entry that names every user-visible product change since `v0.2.0-alpha.15` and no
  development infrastructure.

**Non-Goals:**

- New fixes. Each one has its own Change.
- GitLab publication. It follows after the owner reports the intranet available.

## Decisions

- **Release notes cover the product only.** The CI supply image now builds in CI mode, but no
  adopter consumes that image, so the entry omits it.
  Refactors that change no observable behavior, such as the shared native reference observation,
  are omitted as well.
- **Known advisories are disclosed.** npm 12.2.1 is a production Node dependency. The wheel build
  hook packages it under `ethos/resources/node_modules`, and runtime materialization uses it, so
  the wheels and installed runtimes carry it; the development and CI supply do too. Its bundled
  undici 6.29.0 and ip-address 10.7.2 carry known advisories that no npm release fixes yet. The
  dependency gate reports them without blocking, as its policy requires for findings with no
  fixed stable release. The entry states them under Security, including where they ship.
- **GitHub first.** `dev`, `main`, the tag and the release go to GitHub. The GitLab publication
  and its hosted run stay pending until the owner's notice; they are not claimed.

## Risks / Trade-offs

- [An advisory appears between the proof and the tag] → The release owner runs the release
  build's own audit on the exact head immediately before tagging, and tags only on a pass.
