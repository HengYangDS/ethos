# Tasks

## 1. Adoption plans the pin

- [x] 1.1 Add the regression `tests/unit/adoption/test_pin.py`. Done when it fails before the code
      for a repository without a Mise configuration, with the exact pin, with its own tools, with
      an `http:ethos` table, with another version and with the options form.
- [x] 1.2 Make the paradigm repair's in-place setter and field remover public. Done when
      `set_toml_value` and `without_field` are importable and the paradigm repair tests pass.
- [x] 1.3 Plan the pin as a binding of `adoption_plan`, with a `diff` on every step and `relock`
      in the plan. Done when the plan rows of 1.1 pass.
- [x] 1.4 Remove every directory that a failed apply made. Done when the directory test of 1.1
      passes.
- [x] 1.5 Name the release in `adopt_existing` and render `mise lock`. Done when the release and
      development rows of 1.1 pass.

## 2. The exit removes the pin

- [x] 2.1 Name the bare pin in `exit_preview` and remove it in the fenced apply, with its prior
      bytes in the compensation set. Done when the exit rows of 1.1 pass and the existing exit
      test modules pass unchanged.

## 3. Package acceptance, documents and budgets

- [x] 3.1 Pass the release case to the brownfield acceptance and relax the MCP acceptance to the
      two bindings. Done when the brownfield unit test passes its release rows.
- [x] 3.2 Describe the pin step and its exit in `docs/architecture/adoption-profiles.md` and add the
      changelog entry. Done when Prettier and the prose gate accept both files.
- [ ] 3.3 Measure the source budget. Done when product, tests and tools are at most 82, 175 and 6
      line-equivalents above the lane base.

## 4. Lane, hosted and owner tasks

- [x] 4.1 Apply this Change after `github-pin`. Done when `ethos.repository.release.pin` on the lane
      head exports `bare_entry`, `declared_pin` and `DeclaredPin.key` as this Change calls them.
- [ ] 4.2 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
- [ ] 4.3 Pass the release build's install smoke at the release Change. Done when its brownfield
      stage records three planned files and the MCP stage passes.
- [ ] 4.4 Owner: confirm that `mise lock` carries no directory, or choose a directory-bound form.
      Done when the decision is recorded in this Change's design.
