# Design

## Context

See [proposal.md](proposal.md) and the reviewed draft `supply-image-currency/design-draft.md`,
kept in the session work directory. The Dockerfile hashes eight files into `input.sha256`. Its smoke
stage checks them against the checkout, and each GitLab job checks them first. The GitHub
`supply-image` job builds from the dispatching commit.

## Goals / Non-Goals

Goals:

- A lane that changes a manifest input cannot pass its local proof until it binds a matching image.

Non-goals:

- Recording the manifest itself. It depends only on the built commit.
- Putting bind data in a hashed file. That would create a chicken-and-egg loop.

## Decisions

- **Record the built commit.** The smoke stage proves that the image's manifest matches its build
  commit, and the Git blobs equal the checkout bytes. So the commit identifies the manifest exactly,
  and the check needs no fetch.
- **Check in `ci-projection`.** That gate has no dependencies and already hashes its inputs, so a
  stale image fails in seconds, before every proof gate.
- **One list.** The check parses the Dockerfile's `sha256sum` list with the parser the tests
  already use. GitLab's bootstrap tool list is rendered from the Dockerfile's `native.py` tool list.

## Risks / Trade-offs

- The lane sequence gains one hosted step: publish to GitHub, build and bind before the proof. That
  step already existed, by memory; now the gate enforces it.
