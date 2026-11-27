+++
title = "No file or command enumerates the paradigm's obligations, so a printed total cannot be checked"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Read the declaration's reporting list for the obligations that report; count none by hand."
+++

The entry of 0.2.0-beta.11 printed "47 obligations: 45 refuse and 2 report". No file lists the
obligation ids, and no command or test counts them: an id is the first argument of a call that
raises a paradigm gap, and the reporting list is not held against any set. A scan of the source for
those arguments finds 51 distinct ids at 0.2.0-beta.11, so the printed total is not that count.
The entry of 0.2.0-beta.12 prints no total.

The reporting list also holds `staged-openspec-tree`, which the staged admission raises and the
paradigm report does not, so "the paradigm's obligations" names two sets until one enumeration
defines it.
