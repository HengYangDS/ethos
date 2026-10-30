# Design

## Context

See [proposal.md](proposal.md). `pyproject.toml` is the one declaration of the installed
resources: the wheel's `force-include` maps each shipped document under `ethos/resources/docs/`,
and the sdist's `only-include` lists the same documents. The installed-navigation test stages the
package from that declaration and requires every relative link in an installed document to resolve
inside it, unless the link is labelled `source-only`.

## Goals / Non-Goals

**Goals:**

- Installed navigation resolves again, and installed ETHOS keeps the text that the command plane
  carried before `documents-within-ceiling`.

**Non-Goals:**

- Changing which other documents ship, or the navigation test.

## Decisions

### 1. Ship the reference instead of labelling the link source-only

The moved section describes `ethos lane` and `ethos hook`, which an installed ETHOS runs in every
governed repository. A `source-only` label would make the link optional and drop that text from the
installed package. Shipping the reference keeps the installed content unchanged by the split.

### 2. The archive keeps its record

`documents-within-ceiling` is archived; this Change states the omission and its correction instead
of editing the archive.

## Risks / Trade-offs

- [Another installed document links outside the installed set] → The navigation test checks every
  installed document's links and blocks the proof, as it did here.
