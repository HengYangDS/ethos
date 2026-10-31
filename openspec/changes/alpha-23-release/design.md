# Design

## Context

See [proposal.md](proposal.md). The supply Dockerfile hashes eight inputs into the image's manifest.
`VERSION`, the npm launcher's manifest, the CUE image binding and the generated provider files are
outside it, so moving the version and binding the digest do not change the manifest. The workflow's
offline smoke stage checked the image against the checkout it was built from.

## Goals / Non-Goals

**Goals:**

- GitLab runs the release head with a supply whose input manifest matches it.
- One curated `0.2.0-alpha.23` entry names every user-visible change since `v0.2.0-alpha.22` and the
  known advisories in the release's shipped bytes.

**Non-Goals:**

- Changing any supply version. `supply-currency` moved every pin on the same day, and a move that a
  newer release needs lands in its own Change.
- Removing the coupling between a hashed input and the image binding.

## Decisions

- **Bind the image that the hosted workflow built and inspected.** Its digest is read back from
  ghcr.io, and the GitLab supply jobs select it through the CUE owner and `lane project`.
- **Read the advisories on the exact head.** The release build's audit of the landed head decides
  the Security notes, and the tag waits for it again.
- **Tag after `v0.2.0-alpha.22` is accepted.** The two releases share no state, but acceptance of
  the earlier one is the adopters' current path, so its result is known before the next tag.

## Risks / Trade-offs

- [GitLab still refuses the bound image] → The commit-policy job's manifest check names the
  differing input, and the image is rebuilt from the checkout that differs.
- [Another advisory appears before the tag] → The pre-tag audit refuses the tag, and the fix lands
  in its own Change.
- [Adopters rebind twice within a day] → Each rebind is one selector and its proof. A repository may
  go straight to `0.2.0-alpha.23` once it is published, after it meets the code ceiling.
