# Tasks

## 1. Repairs

- [x] 1.1 Derive command identities only from authored Cyclopts names in `python_syntax.py`.
      Done when four inputs record no command: di-effect's `cyclopts.App(name=PUBLIC_COMMAND)`, a
      Typer decorator, a named App under an unnamed root, and an inline `app` in a governed
      document. ETHOS's 52 command identities must stay unchanged.
      (`test_reference_owner_semantics.py` at `4df4b82a7`; ETHOS declares the same 52 identities as
      at `dbb0c797`.)
- [x] 1.2 Keep package-relative imports inside their package in `_Bindings`. Done when
      `from ._a.b import x` records no import and `from .subprocess import run; run(["x"])`
      records no executable.
      (`test_package_relative_imports_stay_inside_their_package` at `4df4b82a7`.)
- [x] 1.3 Own first-party modules from the repository tree and the product import from its
      binding, and delete the literal exceptions in `closure.py`. Done when three cases hold: a
      root or `src/` module is admitted, an undeclared third-party import is refused, and ETHOS's
      semantic closure reports no orphan.
      (`test_repository_tree_owns_its_first_party_modules` at `4df4b82a7`; the lane's survey of
      ETHOS reports no latent refusal.)
- [x] 1.4 Read pixi environments in `installed_distribution_modules`. Done when a pixi
      environment maps a declared distribution and an undeclared one owns nothing.
      (`test_pixi_environment_maps_declared_distributions` at `4df4b82a7`.)
- [x] 1.5 Report every refused reference from patch admission through prewrite. Done when a patch
      with two unowned references names both, with the first as its reason.
      (`test_patch_admission_reports_every_refused_reference` at `4df4b82a7`.)
- [x] 1.6 Parse owners from complete trees only and compute command owners once. Done when two
      checks pass: the reference test modules, and `source-budget` with product lines below the
      baseline count.
      (At `eceec58ed` the reference, admission and hook protocol suites passed, 853 tests, and
      `source-budget` passed with 69,971 product lines against 69,997 at `dbb0c797`.)

## 2. Contract Texts

- [x] 2.1 Add the four requirements to `repository-governance`. Done when strict validation
      passes and the simulated archive leaves every spec valid.
      (At `eceec58ed` the `openspec` gate passed and the simulated archive validated all 12 specs.)
- [x] 2.2 Record the repair under `[Unreleased]` in `CHANGELOG.md`. Done when `markdown-lint`
      and `prose` pass.
      (Both gates passed at `eceec58ed`.)

## 3. Acceptance

- [x] 3.1 Re-run the read-only fleet survey with the lane's source. Done when three things hold:
      the repaired classes are gone, no root gains a refusal, and every residual is a classified
      true gap or follow-up item.
      (418 latent refusals became 243 and no root gained one; the residual is 226 true gaps and
      17 follow-up items.)
- [x] 3.2 Replay di-effect's two prepared patches read-only through the lane's patch admission.
      Done when neither reports `import:yaml` or `executable:app`, and each complete refusal list
      matches the classified expectation.
      (Taplo: 12 refusals, all true gaps. Gitleaks, replayed from its working-tree postimage:
      14 true gaps, where alpha.19 reports 16, including `import:yaml` and `executable:plan`.)

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out and publish `dev` and
  `main` to GitHub and GitLab.
- Release `0.2.0-alpha.20` with adopter acceptance.
