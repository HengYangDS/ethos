# Tasks

## 1. Docstring Owners

- [x] 1.1 Select `DOC102` in the managed Ruff policy and add a CLI surface case that requires help
      text for every registered command. Done when Ruff reports no finding over `src`, `tests` and
      `tools`, and the case passes on this head and fails when one command loses its docstring.
      (Ruff reported no finding over `src`, `tests` and `tools` with `DOC102`; the case passed
      over 47 commands with the other 39 cases of its file in 51 seconds, and failed once an
      undocumented command was registered.)
- [x] 1.2 Retire the `docstrings` gate, its Nox session, policy file, provider package and test, and
      name the new owners in `rules/module-layout.md`, the configuration reference and
      `CHANGELOG.md`. Done when only archived Changes and the changelog's removal entry name the
      provider, the gate or the policy file, and the `lint` and `product_boundary` sessions pass.
      (At `e47c0deac` `lint` passed and `product_boundary` passed in 8 seconds.)

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` and `main` to GitHub and GitLab, and confirm both peers' hosted runs pass.
