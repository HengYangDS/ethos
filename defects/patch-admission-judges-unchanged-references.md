+++
title = "Patch admission refuses a patch for a reference that the touched file already held"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "none"
+++

A patch put to the product's patch admission is judged on every reference in the postimage of each
file it touches, not only on the references it adds. The admitted set is compiled from the
baseline's declarations: a project's declared distributions and first-party modules, declared
gates, profiles and tools. A reference that the file held before the patch and that no declaration
owns therefore refuses the patch, as `product_reference_not_admitted_at_baseline:<kind>:<value>`;
a formatter's patch over a file that imports `pip` was refused so, with `import:pip`. The gap
names the reference, and neither the file nor that the patch did not add it. Found 2026-11-19 in a
governed repository; read again in the source on 2026-11-25, not run.
