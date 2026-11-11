# Design

## Context

See the [proposal](proposal.md). GitHub's page "Creating a default community health file" lists
`ACCESSIBILITY.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, discussion category forms,
`FUNDING.yml`, issue and pull request templates, `SECURITY.md`, a vulnerability report form and
`SUPPORT.md`. It reads each Markdown file among them from the root, `.github/` or `docs/`.

## Goals / Non-Goals

Goals: a governed repository may keep each Markdown community health file at its root.

Non-Goals:

- Requiring any of them; `required_documents` is unchanged.
- The YAML files and templates, which GitHub reads under `.github/`, a Forge entry the catalog
  already admits.
- `GOVERNANCE.md`, which the page does not list.

## Decisions

1. The four names join `[root].entry_documents` in the packaged paradigm catalog. The root catalog
   check and the naming check already read that list, so no code changes.
2. One test adds all four files to a conforming tree and finds no gap; before the change the
   paradigm reports each as an unadmitted root entry.

## Risks / Trade-offs

None: the catalog only admits more names, and no repository loses an admitted entry.
