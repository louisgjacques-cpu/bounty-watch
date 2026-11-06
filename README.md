# bounty-watch

Checks GitHub every 5 minutes for fresh, real-money bounties with no competing pull requests. When one passes every filter, it opens an issue here, and GitHub notifies you. Quiet hours do nothing, so they cost no Claude usage.

When you get an alert, tell Claude "money making 2" and paste the link.

Filters live at the top of `scan.py`: minimum $50, posted in the last 2 hours, 3 comments or fewer, no assignee, no open PR, repo with 20+ stars in a common language, and no crypto, points-only or bot repos.

Run it by hand from the Actions tab with "Run workflow".
