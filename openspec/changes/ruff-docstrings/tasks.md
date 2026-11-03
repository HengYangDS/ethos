# Tasks

## 1. Docstring Owners

- [ ] 1.1 Select `DOC102` in the managed Ruff policy and add a CLI surface case that requires help
      text for every registered command. Done when Ruff reports no finding over `src`, `tests` and
      `tools`, and the case passes on this head and fails when one command loses its docstring.
- [ ] 1.2 Retire the `docstrings` gate, its Nox session, policy file, provider package and test, and
      name the new owners in `rules/module-layout.md`, the configuration reference and
      `CHANGELOG.md`. Done when no tracked file names the provider, the gate or the policy file
      outside archived Changes, and the `lint` and `product_boundary` sessions pass.

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` and `main` to GitHub and GitLab, and confirm both peers' hosted runs pass.
