# Tasks

## 1. Archive preview

- [x] 1.1 Run `archive_readiness_gaps` on the head's tree in the archive preview and block with its
      gaps. Done when a preview of a Change whose merged requirement exceeds 500 characters blocks
      with `openspec_archived_requirement_invalid` and makes no effect, and a valid Change still
      previews `ready_to_archive`. (The preview case blocks on the head's tree; the 43 existing
      archive cases still preview or apply as before.)

## 2. Specification

- [x] 2.1 Write the `command-plane` delta. Done when strict validation and the cumulative archive
      simulation pass. (12 of 12 specs valid; both earlier scenarios are kept word for word.)

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
