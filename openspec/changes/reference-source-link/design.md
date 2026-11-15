# Design

## Context

`pyproject.toml` lists the files that a wheel carries as resources. The command reference,
`docs/reference/command-plane.md`, is one, and `docs/architecture/local-state.md` is not.
`tests/unit/repository/test_context.py` stages those resources and requires every relative link
of a carried page to resolve inside them, unless the link's title is `source-only` and its text
contains "source".

## Goals / Non-Goals

Goals:

- An installed command reference holds no link that cannot resolve.

Non-Goals:

- Carrying the local-state page in the installation. The reference names the selection and the
  pin; the rules stay with their one owner in the source.

## Decisions

1. **Label the link, keep the sentence.** The reader of an installation still learns that the rules
   exist and where the source states them. Alternative, not taken: remove the link, which leaves
   the section without its owner's name.

## Risks / Trade-offs

- None for behavior. The workstation's pre-check did not select the test; that selection is a
  local tool's and is corrected beside this Change, outside the tree.
