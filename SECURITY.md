# Security

Report a vulnerability in ETHOS privately, through GitHub's private vulnerability reporting: open
the repository's **Security** tab and choose **Report a vulnerability**. Do not open a public issue
or pull request for it.

Examples of what to report, a way to:

- land a change on the accepted branch without passing the repository's gates on the exact tree;
- forge or alter an Attestation without the signing key and without detection;
- make a hook or command run code that the repository did not declare.

These are documented limits, not vulnerabilities:

- The landing record is local and self-attested.
- Until an independent approver exists, the caller, person or agent, authorizes its own landing.
- ETHOS governs the accepted branch only where the forge reserves that branch for the identity that
  runs `ethos publish`.

ETHOS has one maintainer, so a report is handled on a best-effort basis with no fixed response
time. A fix ships in a new release whose notes name it; earlier releases, prereleases included, are
not patched.
