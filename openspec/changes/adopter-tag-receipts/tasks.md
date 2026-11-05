# Tasks

## 1. Qualification

- [ ] 1.1 Admit one release-bound proof as recorded. Done when publication tests under a later
      policy show a historical tag catching up, held by every peer and passing the pre-push hook,
      while a missing, altered or inconsistent bound proof refuses by name and a branch keeps the
      current policy; each test fails first.
- [ ] 1.2 Report `already_applied` when no peer changes. Done when the held-tag test reads
      `remote_push: already_applied` with every attempt already applied.

## 2. Rule owners

- [ ] 2.1 Record DR-0018 and the `repository-governance` requirement. Done when strict validation
      and the archive simulation pass and the decision index lists DR-0018.
- [ ] 2.2 Name the change in the Unreleased notes. Done when `changelog_errors` reports nothing.

## 3. Acceptance

- [x] 3.1 Preview ETHOS's `v0.2.0-alpha.8` for GitHub with the lane's code, read-only. Done when the
      preview passes on the tag's release-bound proof, or refuses by name. With the lane's code, the
      context proof and GitHub push admission pass on proof `f0237ea79ed2`, which the tag's release
      record bound; the root's beta.1 runtime refuses the same push with
      `proof_attestation_repository_policy_mismatch`.
