+++
title = "A ref move's policy reads the accepted branch by its short name, which another ref of that name can answer"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Keep no tag or other ref whose short name equals the accepted branch's name."
+++

Two readers of a ref move's policy resolve the accepted head by the branch's short name rather
than by its full ref name. Git resolves a short name through several namespaces before the branch
namespace, so another ref with the accepted branch's name can answer in the branch's place.

Found 2026-11-22 by a review and read in the source; not probed. Whether the reference hook admits
such a ref in a governed repository, and what a judgement made against it then selects, are not
measured. `since` is the release it was read in; an earlier release may hold it too.
