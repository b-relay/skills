---
name: review
description: Use when the user asks for a review loop.
compatibility: Meant for a Claude model as the coordinator. Codex coordinators in T3 Code don't verify through t3_thread_send.
---

# Review

You judge each finding reviewers report, fix what fits the scope with the
smallest change, list the rest as follow-ups, and have the reviewer that found it
verify your fix. Each new round goes to a fresh reviewer, so every round is an
independent read.

Make the most minimal changes possible. Be careful of scope creep, and don't be
scared to push back: review loops grow work one cheap-looking fix at a time.

## Settings

Take each setting from the request; anything it doesn't say uses the default.

- **Target:** the change to review: a branch compared with its base, a PR, a
  commit range, or an uncommitted diff. If the request doesn't make it clear, ask
  before launching anything; a subagent that can't ask returns that question as its
  report.
- **Reviewer:** GPT-6.1 Sol at `high`, or at `xhigh` when the user asks.
- **Rounds:** [one](#when-the-review-is-done). Users often set a different number.

Apply fixes as you go; list them for approval first only when the user asks.
The run authorizes commits and pushes to the target's branch, which is the existing
PR's branch when there is one. It authorizes no new PRs and no issues. A setting
the user changes mid-run applies from the next round. If the
configured reviewer still can't run after one retry, tell the user and wait;
never substitute.

## Severity

Every finding gets one severity:

- **blocker**: the main requested behavior or an explicit acceptance example is
  wrong.
- **should**: another bug likely to affect callers within the task.
- **nit**: rare-path bugs and other low-impact findings.

Unneeded code, tests, and guards are nits even when behavior is correct.

## Evidence

A bug finding comes with a reproduction the reviewer executed: the script and its
output. To show a test gap, break the implementation on purpose and show the
checks still pass.

When a reproduction isn't practical, as for a race, a timing window, an
environment the reviewer can't run, or a design flaw, the reviewer marks the
finding **unreproduced** and gives the concrete path instead: the inputs or
interleaving, the code it runs through by `file:line`, and what it tried. An
unreproduced finding still counts, weighed by how concrete that path is. A finding that some code
isn't needed has nothing to reproduce; it points at those lines in the diff.

## Launch a reviewer

Each round launches one fresh reviewer, given the brief in
[reviewer.md](references/reviewer.md). Launch it with what the host offers:

- **T3 Code:** a new `delegate_task`, with `mode: "async"`, the model and effort
  in `target`, and a new `clientRequestId`. Then end the turn; its completion
  wakes you, even when you are a delegated task yourself. To verify, send the
  note to the reviewer's `childThreadId` with `t3_thread_send`, not a new
  `delegate_task`: the reviewer needs its own conversation, and keeps it after its
  task finishes. The send returns a `taskId` and wakes you the same way;
  `task_cancel` it if you stop first.
- **Codex elsewhere:** a fresh subagent each round, not a fork of your session. Keep each
  one open: it verifies its own findings.
- **Anywhere else**, or for a model the host can't launch: tell the user and stop.

Don't change the working tree while a reviewer reads it. A timeout, an error or
a missing reply is not a report: resume the reviewer (in T3 Code, `t3_thread_send`
to its `childThreadId`) or restart it with the ledger.

In T3 Code, if you are a delegated task, start the message that ends each waiting
turn with "Still working:", because T3 Code may hand it to your parent as your
result. To get the real result, the parent calls `task_status` with the saved
`taskId` and reads `latestTerminalSummary`, or `summary` when that is null.

## Judge every finding

Re-grade each finding, whatever label it arrived with, and check its
reproduction or path, trying one yourself for an unreproduced finding when that
seems within reach. Then:

- **fix** real findings within the task: blockers, shoulds, and nits that are
  easy to fix and on the path the task uses;
- **follow it up** when it is real but outside the task, a rare-path nit, or a
  nit not worth the change: write it up for the final report with the reproduction, cause, suggested
  fix, and acceptance criteria, or extend the follow-up with the same root cause;
- **decline** it when it is speculative, false, style-only, already fixed, already
  a follow-up, or outside the target, and note the reason.

When you think a finding is wrong, answer with evidence: `file:line`, a test, or
command output. Don't agree just to end the loop. Keep one **ledger** for the run: each finding's id, the reviewer
that found it, its severity, outcome, and evidence.

## Fix

1. Make the smallest change that removes the defect, and fix the case that
   happened, not every case that could. Prefer deleting or narrowing code over a
   new lock, cache, helper, or option. Every new option, parameter,
   or behavior traces to a finding and a documented requirement, and every new
   test to a finding. When a finding proposes rejecting input, check whether the
   code can accept it safely instead.
   Keep the decided design: APIs, data formats, module boundaries, and documented
   behavior stay as they are. Change one only when a finding plainly can't be
   fixed without it, and then as little as works; otherwise make it a follow-up.
   Every such change goes in the report's design section.
2. Write a regression test first when it is worth having: watch it fail, then make
   it pass. Skip it when the test adds no meaningful protection, mocks the
   behavior away, or costs more than the fix, and say why in the verification note.
3. Run the checks for what the fixes touch, and `git diff --shortstat <base>`;
   the full checks wait for the report. If review grew the diff beyond what the
   fixes need, cut first, keeping coverage that protects a finding.
4. Commit and push to the target's branch.

## Verify

Once a reviewer's fixes are pushed, send that same reviewer the verification note
from [reviewer.md](references/reviewer.md). Take a still-open finding back through
[Fix](#fix) and verify it again, and judge new findings as before. A fix that broke
something and has no small fix gets reverted and becomes a follow-up, with the
reviewer's evidence. Verifying doesn't use up a round, but a round gets at most
two verifications. Whatever is still open after the second goes to the next
round's reviewer in the ledger, or to the report if no rounds remain.

## When the review is done

Each round starts with a fresh reviewer. If its review finds nothing, or only
nits, the review is done once any nit fixes are verified. Otherwise,
fix and verify, then start the next round, even if the verifying reviewer
approved, unless this was the last round or the round's fixes didn't change production
behavior. Give each new reviewer the whole change and the ledger. Go up to two
rounds past the limit only while a blocker or should about security,
permissions, auth, data loss, or concurrency stays open with evidence.

**The work is approved only when the latest reviewer says it approves the
current diff.** A spent budget, a timeout, an error, or a missing reply is not
approval. Without approval, the report opens with **not approved** and what's
still open, and the work is neither called ready nor merged.

If a finding is still disputed after two replies, keep it for the final report
with both sides in two or three lines each. The user decides there.

## Report

When the review is done, run the repository's full checks. Then
explain the run in the chat, for a reader who didn't watch it.

Open with the verdict: **approved**, or **not approved** and what's still open. If
any fix changed a decided design, follow it with a section headed
**⚠️ Design changes**, one entry per change: what was decided, what it is now, and
the finding that forced it. Then:

- what happened: the reviewer model and effort, the rounds, and why the run
  stopped;
- each behavior change, with a short before-and-after example a newcomer can
  follow;
- fixes with their commits, and the diff size before and after review;
- every follow-up, complete enough to file, then ask whether to file any and
  where; one rooted in a dependency we own belongs in that repository;
- each disagreement left for the user with both sides, and any declined finding
  worth the user's own judgment, with why it was declined;
- the final check results, and the state of the branch and its PR.

Merge only when the user explicitly asked to, and only when the work is approved.
