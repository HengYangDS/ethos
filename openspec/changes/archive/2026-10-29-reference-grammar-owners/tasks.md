# Tasks

## 1. Repairs

- [x] 1.1 Read shell lines through a quote-aware substitution scanner in `commands.py`. Executable
      identities must contain a letter or digit, and only a `$ ` prompt marker is stripped. Done
      when the nesting, arithmetic and false-pass regressions pass: `print` inside `"$(… -c "…")"`
      is not a command, while `git` inside `"$(git …)"` and `wc` inside `$(( $(wc …) + 1 ))` are.
      (`test_shell_reading_follows_posix_nesting` and `test_scripts_keep_posix_redirection` at
      `7aba409a1`.)
- [x] 1.2 Rewrite documentation metasyntax before shell reading in documentation carriers. Done
      when the placeholder and synopsis inputs observe no false command, a command-position
      placeholder is followed by no command, and `ps aux|grep python` keeps both commands.
      (`test_documentation_metasyntax_is_not_a_command` at `7aba409a1`.)
- [x] 1.3 Match retained steps by file, job and digest whatever their POSIX shape. Done when a
      retained PowerShell step yields no reference, and a changed step text is read again.
      (`test_a_retained_powershell_step_is_owned_as_a_whole` at `7aba409a1`.)
- [x] 1.4 Let each Mise `[tools]` entry own its executable name. Done when `cue` and `pixi` are
      owned and `rustup` stays refused.
      (`test_a_mise_tool_owns_the_executable_it_names` and
      `test_native_owner_closure_uses_only_selected_existing_authorities` at `7aba409a1`.)
- [x] 1.5 Own each top-level package as a first-party name. Done when a `.githooks` script's
      sibling package is owned, while a nested standalone module and an undeclared third-party
      import are still refused.
      (`test_package_roots_own_first_party_names` and
      `test_repository_tree_owns_its_first_party_modules` at `7aba409a1`.)
- [x] 1.6 Report the semantic closure in adopter proofs beside the audit reports. Done when an
      adopter's proof lists a latent gap with its carrier and keeps its verdict.
      (`test_adopter_audit_reports_its_semantic_closure_beside_the_verdict` at `7aba409a1`; the
      proof context lists the closure gaps.)
- [x] 1.7 Consolidate the reference observation to fund the additions. Done when the reference
      test modules pass and `source-budget` passes with product lines at or below 70,000.
      (At `7aba409a1` the 51 affected test modules passed, 1,485 tests, and `source-budget` passed
      with 69,983 product lines; `commands.py` has 508 effective lines against the 512 limit.)

## 2. Contract Texts

- [x] 2.1 Add and modify the requirements in `repository-governance`. Done when strict validation
      passes and the simulated archive leaves every spec valid.
      (At `7aba409a1` the `openspec` gate passed and the simulated archive validated all 12 specs.)
- [x] 2.2 Record the repair under `[Unreleased]` in `CHANGELOG.md`, including the newly visible
      references inside double-quoted substitutions. Done when `markdown-lint` and `prose` pass.
      (`markdown-lint` and `prose` passed at `7aba409a1`.)

## 3. Acceptance

- [x] 3.1 Re-run the read-only fleet survey with the lane's source and with the `0.2.0-alpha.20`
      source on the same repository states. Done when the 18 false refusals that ETHOS causes are
      gone, no new false refusal appears, and the newly visible true references are listed per
      root. Publisher's `Join-Path` goes once it records its PowerShell step, and `rustup` stays a
      companion gap.
      (Same-time surveys of 12 roots at `7aba409a1`. Gone: di-effect `.split`, `attempt`,
      `getattr`, `print`, `str`, `control-plane`, `_hook`, `_pre_commit`, `_pre_push`; alphasim
      `debug`, `doctor`, `run`; publisher `+`, `pixi`; proxy `cue`; benchmark `browser`, `crawl`,
      `cue`. Newly visible: di-effect `dirname`, `id`, `pwd`, `sed`, `tr`, `uname`, `wc`;
      aigw-cli `cat`; alphasim `mktemp`, `pwd`, `uname`.)
- [x] 3.2 Time the semantic closure on di-effect with the lane's source. Done when the time is
      recorded in this task.
      (19.0 s and 18.9 s on the di-effect worktree at `7aba409a1`, with 126 reported gaps.)

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out and publish `dev` and
  `main` to GitHub and GitLab.
- Release `0.2.0-alpha.21` with adopter acceptance.
