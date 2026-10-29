# Tasks

## 1. Repairs

- [ ] 1.1 Read shell lines through a quote-aware substitution scanner in `commands.py`. Executable
      identities must contain a letter or digit, and only a `$ ` prompt marker is stripped. Done
      when the nesting, arithmetic and false-pass regressions pass: `print` inside `"$(… -c "…")"`
      is not a command, while `git` inside `"$(git …)"` and `wc` inside `$(( $(wc …) + 1 ))` are.
- [ ] 1.2 Rewrite documentation metasyntax before shell reading in documentation carriers. Done
      when the placeholder and synopsis inputs observe no false command, a command-position
      placeholder is followed by no command, and `ps aux|grep python` keeps both commands.
- [ ] 1.3 Match retained steps by file, job and digest whatever their POSIX shape. Done when a
      retained PowerShell step yields no reference, and a changed step text is read again.
- [ ] 1.4 Let each Mise `[tools]` entry own its executable name. Done when `cue` and `pixi` are
      owned and `rustup` stays refused.
- [ ] 1.5 Own each top-level package as a first-party name. Done when a `.githooks` script's
      sibling package is owned, while a nested standalone module and an undeclared third-party
      import are still refused.
- [ ] 1.6 Report the semantic closure in adopter proofs beside the audit reports. Done when an
      adopter's proof lists a latent gap with its carrier and keeps its verdict.
- [ ] 1.7 Consolidate the reference observation to fund the additions. Done when the reference
      test modules pass and `source-budget` passes with product lines at or below 70,000.

## 2. Contract Texts

- [ ] 2.1 Add and modify the requirements in `repository-governance`. Done when strict validation
      passes and the simulated archive leaves every spec valid.
- [ ] 2.2 Record the repair under `[Unreleased]` in `CHANGELOG.md`, including the newly visible
      references inside double-quoted substitutions. Done when `markdown-lint` and `prose` pass.

## 3. Acceptance

- [ ] 3.1 Re-run the read-only fleet survey with the lane's source and with the `0.2.0-alpha.20`
      source on the same repository states. Done when the 18 false refusals that ETHOS causes are
      gone, no new false refusal appears, and the newly visible true references are listed per
      root. Publisher's `Join-Path` goes once it records its PowerShell step, and `rustup` stays a
      companion gap.
- [ ] 3.2 Time the semantic closure on di-effect with the lane's source. Done when the time is
      recorded in this task.

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out and publish `dev` and
  `main` to GitHub and GitLab.
- Release `0.2.0-alpha.21` with adopter acceptance.
