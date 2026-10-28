# skills

> [!NOTE]
> **This is a mirror.** Its contents are copied from b-relay's private fleet
> repository, where the work happens. Changes made here are overwritten by the
> next copy, and issues and pull requests here aren't watched.
>
> Mirrored from fleet commit `e325cfc`.

The `babysit` agent plugin, as a [Claude Code](https://code.claude.com/docs/en/plugin-marketplaces)
and [Codex](https://learn.chatgpt.com/docs/build-skills) plugin marketplace named `b-relay`:

- `babysit:review`: runs a review loop. Fresh reviewers find issues, you fix what fits
  the task with the smallest change, and the reviewer that found each issue verifies
  the fix.
- `babysit:until`: does X until Y, or waits until Y to do X. It includes
  `scripts/watch`, which waits for a time or for a command to succeed.

## Install

Claude Code:

```sh
claude plugin marketplace add b-relay/skills
claude plugin install babysit@b-relay
```

Codex:

```sh
git clone https://github.com/b-relay/skills
codex plugin marketplace add ./skills
codex plugin add babysit@b-relay
```

The `watch` tests run with `python3 tests/test-watch.py` (Python 3.10+, macOS or Linux).
