+++
title = "The preview of a Change's archive does not read other files' links to its directory"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Search the tree for the Change directory's name before the archive."
+++

The preview of `ethos lane archive-change` does not read the links that other files hold to the
Change's directory. One governed repository reported three such links that failed the
proof's link gate after an archive; that report is relayed and was not measured here. Search the
tree for the directory's name before the archive.
