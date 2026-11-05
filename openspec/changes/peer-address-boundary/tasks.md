# Tasks

## 1. Rule

- [ ] 1.1 Declare the private-address pattern in the paradigm and carry the identical string in
      ETHOS's Gitleaks configuration. Done when tests show the two equal, one corpus judged alike
      by Python and Gitleaks, red on every private class, including a private forge URL, and green
      on documentation forms, the public identity and a redaction marker. Evidence:
      `test_private_address_scan.py`; a mutant of the pattern fails it.
- [ ] 1.2 Keep both content scans to content and staged modes. Done when a test shows a repository
      whose history alone holds an address passing the hook's staged scan and the `secrets`
      session's scan, while a history scan finds it. Evidence: `test_private_address_scan.py`.
- [ ] 1.3 Take the product boundary's address classes from the paradigm's pattern and keep its
      refusal of `localhost` endpoints. Done when a test shows a private literal and a private name
      refused on a product surface, a `localhost` URL still refused, and documentation forms
      admitted. Evidence: `test_product_boundary_remaining_public.py`; the `product_boundary` gate
      passes.

## 2. Current content

- [ ] 2.1 Move every private-class address in tracked content to a reserved form. Done when the
      `secrets` session passes with the rule and the moved tests pass. Evidence: the schema,
      socket, retirement review and module layout tests.

## 3. Messages

- [ ] 3.1 Judge whole commit messages in the `commit-msg` hook above the scissors line, in commit
      creation and in introduced ranges. Done when tests show a body address refused with
      `commit_message_private_address`, a diff below the scissors line and a documentation address
      admitted, and an introduced commit refused with its revision. Evidence: `test_admission.py`;
      a mutant fails it.
- [ ] 3.2 Judge tag messages at tag admission. Done when a test shows a signed tag whose message
      names a private host refused with `release_tag_message_private_address`. Evidence: the
      transport `test_admission.py`; a mutant fails it.

## 4. Record

- [ ] 4.1 Record the change in the CHANGELOG and validate the deltas. Done when `changelog_errors`
      reports none before and after the edit, and strict validation and the cumulative archive
      simulation pass. Evidence: both pass after each commit.
