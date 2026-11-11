# Tasks

## 1. Supply move

- [x] 1.1 Move every pin and lock under the cutoff, except Mise. Done when the Mise tools name the
      newest eligible releases, `uv lock --upgrade` with the cutoff changes nothing more, the npm
      lock holds the newest stable transitive versions before the cutoff, and Mise and its CI
      bootstrap stay at 2026.10.25. In `a5e72b70a` and `7ce08b25b`, against the cutoff: Go 1.27.4,
      Syft 1.57.1 and Grype 0.121.3 with their Mise lock entries, the lock still at revision 3;
      `uv lock --upgrade --exclude-newer` moved seven packages, a plain `uv lock` dropped the
      persisted option and `uv lock --check` passed; the npm lock moved the OpenSpec CLI 1.17.0,
      minimatch 11.0.6, re2js 2.10.0 and axios 1.21.1 and kept all 556 entries, each resolved from
      the public registry; Mise and its CI bootstrap stay at 2026.10.25 after run 43105667507
      refused the locked Python archive.
- [x] 1.2 Rebuild and bind the CI supply image. Done when the bound digest is in
      `.config/ci/pipeline.cue` and the CI projection check passes. Run 43107519676 built and
      published sha256:5315a0b4cfb8ffaf2130c4dc7b7abe362b8c4b5084e3b1a97d267aaa4d46efdc from
      `7ce08b25b`; `c19e549c5` binds it, and the projection check reads conforming.

## 2. Acceptance

- [x] 2.1 Pass the impacted tests and readiness at the committed head. Done when each passes there.
      At `c19e549c5` the 89 affected test modules with `tests/architecture` passed, 2,303 passed and
      2 skipped by design; at `52043a26b`, after the ty rule rename, the static precheck passed with
      no finding and readiness passed 28 of 28 gates.
