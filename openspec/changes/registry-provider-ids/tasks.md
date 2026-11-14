# Tasks

## 1. Registries

- [ ] 1.1 Name every provider reference of the two shipped registries by its catalog ID, and the
      hosted proof wrapper's probe with them. Done when the table-driven test that requires an ID
      for every shipped reference passes.

## 2. Lane acceptance

- [ ] 2.1 Confirm that the installed runtime carries the provider catalog. Done when the installed
      runtime compiles the lane head's gate policy without `gate_registry_invalid`, and both proof
      floors have the digests that the lane compiles.
- [ ] 2.2 Pass the static precheck and readiness at the lane head. Done when each passes on the
      committed head.
