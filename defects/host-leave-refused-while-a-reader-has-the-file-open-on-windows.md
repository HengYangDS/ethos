+++
title = "On Windows a finished host-queue run can report `host_admission_unavailable`"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Read the command's own output for its result; the place is free."
+++

On Windows a run that leaves the host queue while another process has its ticket's record or lock
file open cannot remove that file. The leave is answered `host_admission_unavailable` after a
normal end, and the result carries no exit status of the finished command. The place itself is
free, and a later read removes the file.
