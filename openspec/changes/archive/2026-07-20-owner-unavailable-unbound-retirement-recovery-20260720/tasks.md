## 1. Admission and effect

- [x] 1.1 Add a narrow owner-unavailable mode to the existing unbound native
  retirement transition.
- [x] 1.2 Bind the accepted Chronicle to the exact source lease tuple and
  source-path absence, then reuse the exact generation CAS.
- [x] 1.3 Re-observe before deletion and preserve the existing receipt and
  postcondition contract.

## 2. Regression coverage

- [x] 2.1 Prove success for one absent source path and exact accepted lease
  tuple.
- [x] 2.2 Prove refusal for Chronicle drift and a source path that still
  exists.
- [x] 2.3 Prove the public CLI exposes the explicit recovery flag.

## 3. Lifecycle closeout

- [x] 3.1 Validate strict OpenSpec, claim/evidence, changed-scope routing, and
  focused source/test gates.
- [x] 3.2 Archive the carrier through the official OpenSpec transition. Refresh
  parity if required, execute exact-HEAD proof, land, and close out locally as
  separate governed transitions.
- [ ] 3.3 Re-observe the external target and invoke native exceptional
  retirement only if current accepted policy and the exact live tuple still
  match.
