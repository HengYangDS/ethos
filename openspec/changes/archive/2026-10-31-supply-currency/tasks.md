# Tasks

## 1. Supply Move

- [x] 1.1 Move the Python, npm, Mise, CI and image pins through their owners' native resolvers. Done
      when `uv lock --check` passes, the dependency declaration check reports no gap,
      `mise install --locked` installs the moved tools and `ethos lane project --check` reports the
      projections conforming. (`uv lock --check` passed; the dependencies gate reported no
      declaration gap; Mise installed Node 26.13.0 and CPython 3.14.10 from the moved lock;
      `lane project --check` reported `conforming`.)
- [x] 1.2 Audit the moved supply. Done when the release build's audit of the lane head reports no
      fixable finding and the Unreleased notes name every advisory that it reports in shipped bytes.
      (After the minimatch and glob overrides the lane audit decided `pass` with
      `unfixed_upstream_findings_reported`: npm 12.2.1's bundled undici, ip-address, minimatch and
      glob. The uv audit reported no finding.)
- [x] 1.3 Repair what the moved tools report. Done when the static, OpenSpec, test and package gates
      pass on the moved supply in focused runs. (On the moved working tree the format, lint, ty,
      dependency, Markdown, JavaScript lint and test, configuration, CI template, schema, build,
      import-boundary and prose gates passed after two Vale term fixes, and 939 CI, projection,
      OpenSpec, release and architecture tests passed.)

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` to GitHub.
- Build the supply image from `dev` with the hosted `supply_image` workflow, bind its digest in its
  own Change, and publish `dev` and `main` to both peers with that binding.
