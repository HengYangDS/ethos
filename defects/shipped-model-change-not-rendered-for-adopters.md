+++
title = "A change to the shipped CI model is not rendered for the repositories that use it"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "none"
+++

ETHOS ships one common CI model, and seven governed repositories generate both Forge files from
it. ETHOS's own pipeline does not use that model, so ETHOS's own projection check cannot see what a
change to the model does to those repositories' generated files, and no test or gate compiles a
repository's declaration under a candidate model. The first place such a change is seen is the
copies run before a tag. Found 2026-11-26: a patch that turned one conditional field of the model
into a plain field moved a key in every generated GitLab job, so all seven tracked files would have
differed from the model's output; it passed 416 test targets before a probe that renders the seven
declarations showed it.
