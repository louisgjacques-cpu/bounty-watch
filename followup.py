"""Find Louis's open bounty PRs that need a reply (new maintainer comments or failing checks).

Prints NONE when nothing needs attention. Otherwise writes pr_url to GITHUB_OUTPUT so the
respond job can start Claude. Stops after 3 automatic fix rounds on the same PR.
"""
import os, sys
from scan import api, search, set_output, OWN_REPO

LOGIN = OWN_REPO.split("/")[0] if OWN_REPO else os.environ.get("LOGIN", "")
MARKER = "<!-- bounty-watch-fix -->"
MAX_ROUNDS = 3
BOTS = ("[bot]", "algora", "codecov", "vercel", "netlify", "coderabbit", "sonarcloud", "changeset")


def is_bot(user):
    login = (user or {}).get("login", "").lower()
    return (user or {}).get("type") == "Bot" or any(b in login for b in BOTS)


def main():
    if not LOGIN:
        print("NONE")
        return
    prs = search(f"is:pr is:open author:{LOGIN} -repo:{OWN_REPO or LOGIN + '/bounty-watch'}")
    for p in prs:
        repo = p["repository_url"].split("/repos/")[1]
        n = p["number"]
        comments = api(f"/repos/{repo}/issues/{n}/comments", {"per_page": 100}) or []
        reviews = api(f"/repos/{repo}/pulls/{n}/reviews", {"per_page": 100}) or []
        rcomments = api(f"/repos/{repo}/pulls/{n}/comments", {"per_page": 100}) or []
        commits = api(f"/repos/{repo}/pulls/{n}/commits", {"per_page": 100}) or []

        rounds = sum(MARKER in (c.get("body") or "") for c in comments)
        if rounds >= MAX_ROUNDS:
            continue

        mine, theirs = [], []
        for c in comments + rcomments:
            (mine if c["user"]["login"] == LOGIN else theirs if not is_bot(c["user"]) else []).append(c["created_at"])
        for r in reviews:
            if r.get("submitted_at"):
                (mine if r["user"]["login"] == LOGIN else theirs if not is_bot(r["user"]) else []).append(r["submitted_at"])
        last_commit = max((c["commit"]["committer"]["date"] for c in commits), default="")
        last_mine = max(mine + [last_commit], default="")

        needs = bool(theirs) and max(theirs) > last_mine
        if not needs and commits:
            sha = commits[-1]["sha"]
            runs = (api(f"/repos/{repo}/commits/{sha}/check-runs", {"per_page": 100}) or {}).get("check_runs", [])
            failed = [r for r in runs if r.get("conclusion") in ("failure", "timed_out")]
            needs = bool(failed) and max(r["completed_at"] or "" for r in failed) > last_mine

        if needs:
            print("REPLY", p["html_url"])
            set_output(pr_url=p["html_url"])
            return  # one PR per run
    print("NONE")


if __name__ == "__main__":
    main()
