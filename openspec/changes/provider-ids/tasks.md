# Tasks

## 1. Catalog and resolution

- [ ] 1.1 Add the packaged table and its reader. Done when the table-driven test passes: each ID has
      its own importable callable, and the 23 legacy names map to IDs.
- [ ] 1.2 Accept both reference forms in the declaration contract and the gate schema. Done when a
      gate that names `provider.schemas` validates and the malformed shapes still refuse.
- [ ] 1.3 Resolve providers through the catalog in the runner and in source binding, and add the
      legacy note. Done when both spellings of one provider give one report, and only the legacy
      one adds `gate_provider_legacy_name`.
- [ ] 1.4 Refuse an unresolved provider in the gate policy. Done when a public execution over a
      gate that names `provider.unknown` refuses with `gate_provider_unresolved` and runs no gate.
- [ ] 1.5 Recognize the code axes, source integrity, the JavaScript attempt and the skill portfolio
      by every spelling, and compare shared gates by ID. Done when a shared gate that a repository
      declares by its legacy name composes with one declared by its ID.

## 2. Records

- [ ] 2.1 Add the changelog entry and the configuration reference's line for the table. Done when
      both name the ID form, the note and the refusal.

## 3. Lane acceptance

- [ ] 3.1 Compare the gate policy that the installed runtime and the lane compile for the lane head.
      Done when both proof floors have equal digests.
- [ ] 3.2 Pass the static precheck and readiness at the lane head. Done when each passes on the
      committed head, with product at most 68 and tests at most 90 line-equivalents above the lane
      base.
