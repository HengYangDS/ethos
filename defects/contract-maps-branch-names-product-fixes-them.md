+++
title = "The product design contract says a repository maps its branch names; the product reads no such mapping"
state = "open"
since = "v0.2.0-alpha.5"
fixed_in = ""
workaround = "A repository with other branch names renames them to the fixed names first."
+++

The product design contract says a repository maps its branch names to the roles and may rename
refs. This release reads no such mapping: the names are fixed (`main`, `dev`, `candidate/dev`,
`work/`, `proposal/`), the requirement "Branch roles and Work Lanes use the standard names" governs,
and a repository with other names renames them first.

Declared names are decided (DR-0032); the fixed names are no compatibility promise.
