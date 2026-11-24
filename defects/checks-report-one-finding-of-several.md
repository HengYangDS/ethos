+++
title = "The behavior gate and the commit hook's size check report one finding of several"
state = "open"
since = "v0.2.0-beta.10"
fixed_in = ""
workaround = "The behavior gate's native coverage report, which the gate copies to `ETHOS_NATIVE_OUTPUT_DIR` when that is set, holds the rest. The paradigm report lists every tracked file over the ceiling at once."
+++

Two checks report one finding where they computed several. The behavior gate returns one reason code
without file names; its native coverage report, which the gate copies to `ETHOS_NATIVE_OUTPUT_DIR`
when that is set, holds the rest. The commit hook's size check names the first staged file over the
ceiling, so eight such files take eight attempts; the paradigm report lists every tracked file over
the ceiling at once.
