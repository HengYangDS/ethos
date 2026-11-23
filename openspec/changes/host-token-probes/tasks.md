# Tasks

## 1. The test

- [ ] 1.1 Derive the token test's probes from the token and ask the empty token and a token
      without a nonce. Done when the test passes whatever nonce is drawn, and a comparison of the
      nonce alone and a comparison that ignores where the process number begins each fail it.
- [ ] 1.2 Answer a token by the exact comparison alone. Done when `holds` has no check of the
      token's shape and every probe of the test, malformed or foreign, is still refused.
