# Tasks

## 1. Probe Supply

- [x] 1.1 Make the native supply install and require every declared one of Node, Python and uv
      through Mise. Done when a test that declares them fails before the change and passes after
      it, online and offline. (`test_mise_supply_prepares_every_declared_interpreter_tool` failed at
      `63deedc09` because the install named Node only, and passes online and offline after the
      change; the module's 76 cases passed.)
- [x] 1.2 Declare `uv = "0.13.6"` in `.config/mise/config.toml` and lock it. Done when `mise lock`
      records uv for the six locked platforms, `mise install --locked` installs it and
      `mise which uv` resolves it in the lane. (`mise lock` recorded uv 0.13.6 for linux-arm64,
      linux-x64, macos-arm64, macos-x64, windows-arm64 and windows-x64; `mise install --locked`
      reported every tool installed; `mise which uv` resolved Mise's uv 0.13.6.)

## 2. Supply Move

- [x] 2.1 Move the Python locks through `uv lock --upgrade` and raise the direct floors to their
      locked versions. Done when `uv lock --check` passes and the dependency declaration check
      reports no gap. (`uv lock --upgrade` moved cachetools 7.2.8, filelock 4.2.6, nodeenv 1.12.0,
      platformdirs 4.14.2 and python-multipart 0.0.33, and the quality sample's lock was already
      current; `uv lock --check` and the dependencies session passed; 812 CI, projection, toolchain
      and paradigm tests passed with 1 skipped, and the format, lint, CI template and configuration
      sessions passed.)
- [ ] 2.2 Audit the moved supply. Done when the release build's audit of the lane head reports no
      fixable finding and the Unreleased notes name every advisory that it reports in shipped bytes.

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` to GitHub.
- Build the supply image from `dev` with the hosted `supply_image` workflow, bind its digest in its
  own Change, and publish `dev` and `main` to both peers with that binding.
