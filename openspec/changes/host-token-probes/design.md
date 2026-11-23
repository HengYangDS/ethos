# Design

## Context

See the [proposal](proposal.md). The queue answers a token in `HostQueue.holds`: it splits the
token at its colon, requires a nonce of sixteen alphanumeric characters and a decimal process
number, and then asks whether a live ticket's name ends with `-<process number>-<nonce>`.

## Goals / Non-Goals

Goals:

- A test of the token that cannot fail for the nonce it happens to draw.
- Probes that reach the comparison, so the test binds "exactly one ticket's".

Non-Goals:

- Any change of the token's form or of an answer that `holds` gives.

## Decisions

1. **Every probe is derived from the token.**
   - **Rests on:** the token's form, `<nonce>:<process number>`, read in `Ticket.token`.
   - **Decision:** the well-formed probes are the nonce with the process number plus one, the
     process number with a nonce whose first character is replaced by another hexadecimal
     digit, the nonce with the process number preceded by `1`, and the nonce with the process
     number less its first digit. Each differs from the token for every nonce.
   - **Why not keep the upper-case probe:** it differs from the token only when the nonce holds a
     letter.
2. **The malformed probes stay and gain two.** The patterns that a glob would have matched stay,
   and the empty token and a token without a nonce return.
3. **The shape check goes.**
   - **Rests on:** a mutation that removes the check passes every probe of this test, also the
     malformed ones, and this reading of the comparison. A ticket's name is twenty digits, a
     dash, the process number, a dash and the nonce, and neither the process number nor the
     nonce holds a dash. The comparison asks whether the name ends with a dash, the token's
     process number, a dash and the token's nonce. Nothing stands before the name's first
     digit, so that tail can begin only at the dash before the process number: the token's two
     parts are then exactly the ticket's.
   - **Decision:** `holds` splits the token at its colon and compares. A value that is no token
     costs one read of the locks and is answered that it holds nothing, as before.
   - **Why not keep it as a second guard:** a guard that no input reaches is not checked by any
     test, and its comment gave a reason, patterns, that the comparison already answers.

## Risks / Trade-offs

- [The replaced first character could equal the original] -> The replacement is chosen as the
  digit that the original is not.

## Proof Strategy

The test passes on the lane's code. Two mutations of `holds` are run against it and each fails
it: a comparison of the nonce alone, and a comparison that ignores where the process number
begins. The four other modules that use the queue pass unchanged.
