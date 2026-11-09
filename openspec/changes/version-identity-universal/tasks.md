# Tasks

## 1. Behaviour

- [ ] 1.1 Require a version identity of every governed repository. Done when paradigm tests show
      an untagged repository without `VERSION` reported once, its repair naming a manifest's
      version, the tag pattern checked only with release tags, an untagged repository without
      `LICENSE` reporting no license gap, and the conforming tree carrying `VERSION` and a
      changelog.
- [ ] 1.2 Seed only what no owner chooses. Done when a repair test creates an absent changelog and
      leaves a malformed one, and a formation test shows a formed repository with both files and no
      version-source or changelog gap.

## 2. Acceptance

- [ ] 2.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there.
