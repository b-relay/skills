# What reviewers get

## The brief

Write one brief that every reviewer gets. A reviewer sees none of your
conversation, so the brief stands alone. Include:

- the target, any authoritative sources (spec, ADRs, tickets) to verify the
  code against, and the commands the reviewer may run;
- that tracked files are read-only, and scratch reproductions go in its own test
  folder outside the repository;
- that the reviewer completes the review itself, without delegating to another
  agent or model;
- the [Severity and Evidence](../SKILL.md#severity) sections, word for word;
- the nearby redesigns and tickets the reviewer leaves alone, or "none";
- from round 2 on, the ledger: findings already fixed, followed up, or declined,
  to leave alone unless one is wrong;
- that its final message is the complete report: findings most severe first, each
  with a stable id, severity, location, the reproduction or unreproduced path, and
  a suggested fix, then whether it approves, which it does when no blocker or
  should is open on the current diff.

## The verification note

Once its fixes are pushed, send the reviewer that found them the new commit, the
ledger entries for its findings, and the change since its review. Ask it to:

- re-run its reproductions to check the fix. For a behavior fix, show that the
  reproduction and any new test fail with only that fix reverted, in a copy
  outside the repository; for a test-only fix, show the gap is closed; for
  removed code, show it's gone and nothing used it;
- mark each of its findings `resolved` or `still open`, with executed evidence;
- report anything the fixes broke as a new finding;
- end by saying whether it approves the current diff.
