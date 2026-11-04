# Tasks

## 1. Identity forwards

- [x] 1.1 Make module layout refuse an identity forward. Done when a test shows that a function
      forwarding every parameter to a defined or imported function, positionally, by keyword or
      by unpacking, yields `module_layout_identity_forward:<path>:<function>`, while a changed,
      reordered or added argument, a dictionary method, a computed receiver and a decorated
      function do not, and the test failed before the change. It failed on the missing check; its
      11 cases pass. The check reads the product package, since four test fixtures that only
      supply defaults would otherwise count.
- [x] 1.2 Remove the last identity forward. Done when `openspec_base_command` owns the command
      resolution, the module-layout gate passes on the lane head, and the OpenSpec, CLI, adoption
      and lane tests pass. The layout report is clean, the 16 test modules that use the name pass
      (565 tests), and 3,404 OpenSpec, CLI, adapter, adoption, lane, policy and architecture
      tests passed before the run's 15-minute bound.
- [x] 1.3 Name the refusal in `rules/module-layout.md` and the changelog. Done when the import
      discipline section and the unreleased Changed section name it.
