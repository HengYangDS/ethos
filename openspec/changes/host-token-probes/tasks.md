# Tasks

## 1. The test

- [x] 1.1 Derive the token test's probes from the token and ask the empty token and a token
      without a nonce. Done when the test passes whatever nonce is drawn, and a comparison of the
      nonce alone and a comparison that ignores where the process number begins each fail it. (At
      `3362f128b`, `test_a_token_names_one_ticket_exactly` passes with nine malformed probes,
      five foreign ones asked unconditionally and the nonce in upper case where it has a letter,
      each derived from the token. A comparison of the nonce alone fails it, and so does a
      comparison without the dash before the process number.)
- [x] 1.2 Bind the check of a token's shape. Done when a held lock file whose name is not a
      ticket's answers for no value, and the removal of the check fails the test. (At
      `3362f128b` the test holds `x--.lock` and `a-b-c-d.lock` and is refused for the empty
      value, `:` and `d:b-c`; without the shape check it fails. `holds` is byte for byte that of
      `2f232aa08`, and the six modules that use the queue pass, 166 cases.)
