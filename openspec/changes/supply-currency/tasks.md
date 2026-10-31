# Tasks

## 1. Supply Move

- [ ] 1.1 Move the Python, npm, Mise, CI and image pins through their owners' native resolvers. Done
      when `uv lock --check` passes, the dependency declaration check reports no gap,
      `mise install --locked` installs the moved tools and `ethos lane project --check` reports the
      projections conforming.
- [ ] 1.2 Audit the moved supply. Done when the release build's audit of the lane head reports no
      fixable finding and the Unreleased notes name every advisory that it reports in shipped bytes.
- [ ] 1.3 Repair what the moved tools report. Done when the static, OpenSpec, test and package gates
      pass on the moved supply in focused runs.

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` to GitHub.
- Build the supply image from `dev` with the hosted `supply_image` workflow, bind its digest in its
  own Change, and publish `dev` and `main` to both peers with that binding.
