# Tasks

## 1. The place

- [ ] 1.1 Pass the ticket's lock to the admitted command. Done when a holder killed with `SIGKILL`
      while its command runs keeps the place until that command ends, and a second run is admitted
      only then.
- [ ] 1.2 Release the lock for every inheritor when the holder leaves. Done when a holder that
      leaves frees the place at once while a process its command started still has the lock open.
- [ ] 1.3 Probe without creating. Done when a read of a queue whose lock file vanished creates no
      file and removes none.

## 2. The read and the token

- [ ] 2.1 Name the holder's state. Done when the read lists a held ticket whose holder is gone as
      `holding` with `holder` `gone`, and no process is signalled where the platform is not POSIX.
- [ ] 2.2 Join by the lock. Done when a command started by work that outlived its holder joins
      that place, and a token whose lock is free admits nothing.

## 3. Evidence

- [ ] 3.1 Run the journey with the built command. Done when `SIGKILL`, `SIGHUP` and a clean end
      with a surviving descendant are each recorded with the queue's readings.
- [ ] 3.2 State the change in the changelog. Done when the Unreleased entry names the repair, the
      platforms it covers and the case of a process that never ends.
