# Tasks

## 1. Absorbed proposals

- [x] 1.1 After an applied publication of the accepted branch, list each moved peer's proposal refs
      whose tips the published head preserves, and name their retirement probe as the next action.
      Done when a focused test shows an absorbed proposal named on both peers, an unabsorbed one
      omitted, and the named probe ready to retire.
      (`test_accepted_publication_names_the_proposals_it_absorbed`; the 19 publication and closeout
      modules pass, 359 cases.)
- [x] 1.2 Report a peer whose proposal listing fails as unobserved without changing the
      publication's state or verdict. Done when a focused test with a failing listing keeps state
      `published` and names that peer.
      (`test_an_unreadable_proposal_listing_is_reported_not_read_as_empty`.)

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
