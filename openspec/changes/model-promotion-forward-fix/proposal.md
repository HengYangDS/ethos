# Change: Unblock accepted publication with exact proof and locked runtime closure

Accepted publication currently evaluates the generic same-HEAD proof set, so a
retired Work Lane generation can veto the repository proof that actually owns
publication. Source-built hook runtimes also install the ETHOS wheel without the
project lock, allowing offline installation to re-resolve a newer transitive
version than `uv.lock`.

This change binds publication to the accepted HEAD's exact repository
Commitment and installs source-built runtimes from the existing locked closure.
It does not change generic Work Lane proof semantics, add a proof store, or add
dependency pins outside the project lock.

Capabilities: `repository-governance`, `distribution`.
