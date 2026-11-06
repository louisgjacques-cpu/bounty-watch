# bounty-watch

Checks GitHub every 5 minutes for fresh, real-money bounties with no competing pull requests. When one passes every filter, it opens an issue here, tags you, and starts Claude on the fix. Quiet runs don't use Claude at all.

## How a hit goes

1. The scan finds a bounty and opens an alert issue here. Your phone pings.
2. Claude runs inside GitHub Actions on your Claude plan. It forks the project, makes the fix, runs the tests and pushes a branch to your fork. If it can't do a clean job, it comments "Skipped" with the reason instead.
3. Auto mode (the default): Claude posts the `/attempt` claim and opens the pull request itself, under your name, with `/claim` for Algora.
   Review mode: set the repository variable `AUTO_SUBMIT` to `false` (Settings → Secrets and variables → Actions → Variables). Claude then comments on the alert with a one-tap link to open the PR yourself.
4. Every 5 minutes it also checks your open bounty PRs. When a maintainer comments or a check fails, Claude makes the changes, pushes them and replies. It stops after 3 rounds on the same PR.
5. At most 3 bounties a day get solved, to protect your Claude usage. Extra hits still get an alert.

## Secrets this needs

- `CLAUDE_CODE_OAUTH_TOKEN`: run `claude setup-token` on your computer and paste what it prints.
- `BOT_PAT`: a classic GitHub token from louisgjacques-cpu with only the `public_repo` scope. Claude uses it to fork, push and comment.

## Filters

These are at the top of `scan.py`: at least $50, posted in the last 2 hours, 3 comments or fewer, no assignee, no open PR, and a repo with 20+ stars in a common language. Crypto, points-only and bot repos are skipped.

## Testing

Actions tab → bounty scan → Run workflow. Paste any GitHub issue link into "test_url" to make Claude try it right away.
