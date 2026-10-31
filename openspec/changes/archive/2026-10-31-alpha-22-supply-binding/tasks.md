# Tasks

## 1. Supply Binding

- [x] 1.1 Bind the published supply digest through the CUE owner and regenerate the projections.
      Done when `lane project --check` reports the projections conforming and every GitLab supply
      job selects the new digest and none the previous one. (Run `41161196308` built and pushed the
      image from `16a43a623` in 3 minutes; `lane project --check` reported `conforming`; the five
      GitLab supply jobs select `d821c4f7…` and none `e7e820a9…`.)

## 2. Release Entry

- [x] 2.1 Fold the Unreleased notes into the `0.2.0-alpha.22` entry. Done when the changelog
      validates with 0.2.0-alpha.22 as its release target, the Unreleased section is empty, and the
      entry names every advisory that the release build's audit of the lane head reports.
      (`changelog_errors` with target 0.2.0-alpha.22 reported none and the 74 version tests passed.
      The audit of `96c96adef` decided `pass` and reported only npm 12.2.1's bundled undici,
      ip-address, minimatch and glob, which the entry names; uv 0.13.6 still embeds rustls 0.23.45,
      as its `Cargo.lock` at tag 0.13.6 shows.)

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` and `main` to GitHub and GitLab.
- When the landed head's hosted runs pass, tag it with `ethos land --release`, publish the tag to
  both peers, dispatch the hosted release, verify the published assets, accept the adopter path and
  relay the identities to the adopter owners.
