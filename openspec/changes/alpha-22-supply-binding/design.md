# Design

## Context

See [proposal.md](proposal.md). The supply Dockerfile hashes eight inputs into the image's manifest.
The CUE image binding and the generated provider files are outside it, so binding the digest does
not change the manifest. The workflow's offline smoke stage checked the image against the checkout
it was built from.

## Goals / Non-Goals

**Goals:**

- GitLab runs the release head with a supply whose input manifest matches it.
- One curated `0.2.0-alpha.22` entry names every user-visible change since `v0.2.0-alpha.21` and the
  known advisories in the release's shipped bytes.

**Non-Goals:**

- Changing any supply version, which `supply-currency` owns.
- Removing the coupling between a hashed input and the image binding.

## Decisions

- **Bind the image that the hosted workflow built and inspected.** Its digest is read back from
  ghcr.io, and the five GitLab supply jobs select it through the CUE owner and `lane project`.
- **Keep the version and date.** Nothing was tagged as `0.2.0-alpha.22`, so its entry still
  describes the next release, and the release follows on 2026-10-31.
- **Read the advisories on the exact head.** The release build's audit of the landed head decides
  the Security notes, and the tag waits for it again.

## Risks / Trade-offs

- [GitLab still refuses the bound image] → The commit-policy job's manifest check names the
  differing input, and the image is rebuilt from the checkout that differs.
- [Another advisory appears before the tag] → The pre-tag audit refuses the tag, and the fix lands
  in its own Change.
