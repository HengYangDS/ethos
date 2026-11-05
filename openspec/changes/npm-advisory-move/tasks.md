# Tasks

## 1. Supply

- [x] 1.1 Pin npm 12.2.2 and lock it natively. Done when the lock moves npm and only its seven
      bundled packages, `npm ci` installs it, and the dependency audit reports no unapproved
      finding. It moves exactly those eight, `npm ci` added 408 packages, and the release audit
      passes with glob and minimatch reported as unfixed upstream.
- [x] 1.2 Record the move in the `0.2.0-beta.2` entry. Done when the changelog validates and the
      entry names the six fixed advisories, the two remaining ones and the age exception. The
      release tests pass, and every earlier entry is unchanged.
