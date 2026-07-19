## Tasks

- [x] Identify the native deadlock: admission rejects an active lease while the
  receipt requires that lease to be absent.
- [x] Add the exact-holder/lease/head CAS relinquishment inside the native
  exceptional transition.
- [x] Reobserve retirement bindings after relinquishment before ref deletion.
- [x] Add matching-holder success and delete-failure regressions.
- [x] Add dated claim, Chronicle, canonical delta, and command documentation.
- [ ] Run strict lifecycle, quality, exact-HEAD proof, candidate land, and
  accepted-root closeout.
