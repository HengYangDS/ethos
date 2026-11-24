+++
title = "A code span of two or more words in a document can be read and refused as a command"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Write the phrase without a code span, or as spans of one word."
+++

A code span of two or more words in a document can be read as a command line, and its first word is
then held against the executables that the baseline admits:
`product_reference_not_admitted_at_baseline:executable:<word>`. Write the phrase without a code
span, or as spans of one word.
