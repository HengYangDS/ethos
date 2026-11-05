# Tasks

## 1. Refusal

- [x] 1.1 Raise every gap of the commit message refusal. Done when the architecture test, which
      failed in `ib1`, finds no first-gap transport, and the commit creation and admission tests
      pass. The architecture test failed in `ib1` on `creation.py:161`. With `refusal(*gaps)` it
      finds no first-gap transport, and with the commit creation and admission tests 91 pass.
