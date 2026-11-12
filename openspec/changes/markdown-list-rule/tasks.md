# Tasks

## 1. The rule and its gate

- [ ] 1.1 Add the pure spacing pass with tests for each list shape. Done when a stray blank line, a
      blank line before an introduced block and a missing separator after a spread item are each
      found and repaired, and a second pass changes nothing.
- [ ] 1.2 Apply the pass in the Markdown postimage and in `pre-commit`. Done when the formatting
      gate refuses a violation that Prettier accepts, `ethos lane format --apply` repairs it, and a
      staged violation refuses with its path and line.
- [ ] 1.3 Repair ETHOS's two violations and add the Changed line. Done when the rule finds no
      violation in ETHOS's authored Markdown and Prettier and Vale accept the changed files.

## 2. Acceptance

- [ ] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
