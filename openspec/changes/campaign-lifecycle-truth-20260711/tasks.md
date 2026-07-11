## 1. Campaign Truth Contract

- [x] 1.1 Add failing regression coverage for active steps backed only by an archived carrier, terminal steps backed only by an active carrier, and an honest waiting campaign state.
- [x] 1.2 Extend the campaign validator so carrier topology and closeout state agree with each step lifecycle state.
- [x] 1.3 Reconcile the hooked-write-admission campaign step from its accepted and candidate reflog heads and its dated Chronicle.

## 2. Governance Surfaces

- [ ] 2.1 Update the canonical repository-governance OpenSpec specification with the carrier-bound campaign lifecycle requirement.
- [x] 2.2 Explain the active-carrier, archived-carrier, and planned-successor boundary in campaign governance documentation.

## 3. Evidence And Closeout

- [x] 3.1 Add a bounded claim and dated Chronicle for the reconciliation and validator.
- [ ] 3.2 Run focused tests, format/lint, campaign/OpenSpec lifecycle checks, claims, generic parity, and full executed proof.
- [ ] 3.3 Archive the completed OpenSpec carrier, land through candidate and accepted-root closeout, retire this Work Lane, and leave remote publication deferred.
