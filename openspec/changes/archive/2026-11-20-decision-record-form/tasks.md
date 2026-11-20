# Tasks

## 1. The text

- [x] 1.1 Add DR-0031 and the Docs Registry's section "Decision records", and replace the
      registry's former paragraphs on decision records. Done when both files pass markdown-lint,
      prose, the docs registry and the local link check, and no other document links an anchor
      that the replaced paragraphs carried.
      (At `1daed61a3` the row's 26 paths, DR-0031 and the registry document among them, pass the
      Markdown lint and the prose gate with a refusing control, the docs registry passes, and their
      local links resolve, 135 of 135. At `9e0d470d5` other tracked documents link three anchors of
      the registry document, and all three exist.)
- [x] 1.2 Apply the delta of `repository-governance`. Done when OpenSpec validates the Change
      strictly, the archive of the delta validates on a copy, and each modified requirement
      restates every scenario it keeps.
      (At `1a424cd9e`: the archive of the delta validates on a copy, 12 of 12 specifications. The
      rule on keeping records is an added requirement, because the modified one passed the text
      bound with it.)

## 2. ETHOS's own first step

- [x] 2.1 Bring every record under `docs/decisions/` to the form's first step with the
      first-step tool, and add DR-0032. Done when a second run of the tool changes nothing and
      the tool lists nothing for a person.
      (At `9e0d470d5` a second run of `dr-migrate.py check` reads 25 records, changes no file and
      lists nothing for a person. DR-0032 is in `1daed61a3`; `c4a866783` dates the seven removed
      records.)
- [x] 2.2 Declare each update among the records and mark each replaced or extended sentence or
      list item in the older record. Done when a reader other than the lead has prepared each
      pair from the two records, each pair carries `updates` and `updated_by`, and no sentence
      or list item carries two marks.
      (Three readers prepared 18 candidate pairs from the records; 14 are updates and 4 only cite.
      At `1daed61a3` each of the 14 carries `updates` and `updated_by`, with 28 marks in ten older
      records. One sentence that two records had changed carries one mark that names both.)
- [x] 2.3 Write the index as the form's table. Done when every number from 1 to the highest has
      a row, each removed number's row names where Git holds it, and the README holds no rule
      text.
      (At `09244d591` the index has one row for each number from 1 to 33, each removed number's row
      names the commit and path where Git holds it, and the page holds its two entry paragraphs, the
      table and the legend.)

## 3. Acceptance

- [x] 3.1 Pass the precheck and readiness at the lane head. Done when each passes on the
      committed head and the hosted runs of that head pass on both forges.
      (At `7bd573ad9` on 2026-11-20 the pre-check passes with no finding and readiness passes with
      its 28 gates. The pre-check ran its full selection at `a9e90ab6f`, 413 test modules, 8,337
      passed and 3 skipped, and from there the selection of the one test file that differs, 43
      modules, 371 passed and 1 skipped.
      GitHub's push run 44655144202 and GitLab's pipeline 16815 of `7bd573ad9` pass. The run's
      link observation, which may fail, counted three redirects; `64c12fc64` names those
      sources at their new addresses.)
