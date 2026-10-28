---
name: until
description: Use when asked to do X until Y or wait until Y to do X.
---

# Until

The ping is the time or condition the user names: "until 17:00 ET", "when CI
passes", "until the backlog is empty". Either keep working until the ping ("keep
going until 17:00"), or wait for it and then act ("when CI passes, merge it", or
just "tell me when CI passes"). If the work finishes first, stop then.

If the user hasn't given a ping, ask before starting. A later message, such as
"continue until 11:30 ET", replaces it.

Every ping has a deadline, when you give up. A time is its own deadline. For a
condition, pick a deadline that fits the task.

## Wait

Nobody will prompt you again, so until the run finishes, never end a turn without
a wake armed for the ping and for its deadline. Use these rather than your own
watcher or repeated sleeps, unless none of them fits:

- **A time, or a condition a command can check:** this skill's
  [`scripts/watch`](scripts/watch), by its absolute path. `watch 17:00` exits at
  the next 17:00 local time; for another zone, pass an ISO time such as
  `2026-10-28T17:00-04:00`. `watch 2h -- test -e out/done` runs the command every 30 seconds and
  exits 0 when it succeeds, or 2 if two hours pass first, so it covers the
  deadline too. `watch --help` gives the rest.
- **A pull request, in T3 Code:** first act on its current checks and comments,
  then `watch_pull_request`. It wakes you when a check fails, the required checks
  pass, someone else comments or reviews, or the branch conflicts. Only the
  thread that owns the PR watches it, never a delegated task.
- **Delegated work, in T3 Code:** `delegate_task` with `mode: "async"`; its
  completion wakes you.

The last two have no deadline, so also run `watch <deadline>` with no command.

However you use `watch`, run it so its exit wakes you:

- **Claude Code**, including inside T3 Code: with `run_in_background: true`.
- **Codex inside T3 Code:** in an async `delegate_task` on GPT-6 Luna or Claude
  Haiku 5.5, either at `high`, whose only job is to run it and report its last line
  and exit code.
- **Codex elsewhere**, which can't be woken once its turn ends: stay in the turn,
  start it with the shell tool, and keep reading that shell session until it
  exits.

A wake means something changed, not that the ping came: read the current state
before acting, and act on each change once. If the ping hasn't come, re-arm
whatever ended and carry on. Re-arm too when the ping changes.

In T3 Code, if you are a delegated task, start the message that ends each waiting
turn with "Still working:", because T3 Code may hand it to your parent as your
result. To get the real result, the parent calls `task_status` with the saved
`taskId` and reads `latestTerminalSummary`, or `summary` when that is null.

Any other subagent is never woken once its turn ends, so it waits in its turn:
run `watch` in the foreground, and run it again if the shell call times out
first. This takes precedence over the routes above.

## Work

1. Read the state the ping depends on, such as the CI run, a file, or the remote
   branch (fetch first only for remote Git state). Arm the wakes, and tell the
   user what they are and the deadline.
2. If there is work, do it without pausing, as if the user is away. Between
   steps, check the clock or the wake instead of asking whether to continue.
3. When a decision needs the user, write the question and its context to a
   questions file (make it with `mktemp`, outside the repository, and tell the
   user its path), and carry on with what doesn't depend on it. When
   everything left depends on an answer, finish.

## Finish

When the ping comes, the deadline passes, or the work is done or blocked:

1. Stop this run's watchers. In T3 Code, `task_cancel` each watcher task and
   `unwatch_pull_request` each watched PR.
2. If you were working until the ping, stop the work at once, even mid-step,
   along with its background tasks, processes, and subagents, and save it with a
   note of what's left so it can be picked up later. If you were waiting to act, act only if the ping came by
   the deadline; otherwise tell the user why you stopped.
3. Report as the task normally would, plus what's left, then ask every question
   still open in the questions file. Then wait: a new instruction or ping starts
   a new run.
