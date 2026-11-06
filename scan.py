"""Hourly bounty scan. No dependencies, runs on GitHub Actions.

Finds fresh, real-money GitHub bounties with no competition and opens one issue
per hit in this repo (which triggers a GitHub notification). Quiet runs do nothing.
Set DRY_RUN=1 to print hits instead of opening issues.
"""
import json, os, re, sys, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta, timezone

TOKEN = os.environ.get("GITHUB_TOKEN", "")
OWN_REPO = os.environ.get("GITHUB_REPOSITORY", "")  # owner/name, set by Actions
DRY_RUN = os.environ.get("DRY_RUN") == "1"
HOURS_BACK = int(os.environ.get("HOURS_BACK", "2"))
OWNER = OWN_REPO.split("/")[0] if OWN_REPO else ""

MIN_USD = 50
MAX_COMMENTS = 3
MIN_STARS = 20
LANGS = {"Python", "TypeScript", "JavaScript", "Go", "Rust", "Java", "Ruby", "PHP", "C#", "Kotlin", "Swift", "Dart", "Shell", "HTML", "CSS", "MDX", "Vue", "Svelte", "Elixir", "Scala"}

# Repos and wording that were junk in Nov 2026 scans
SPAM_REPO = re.compile(r"bounty-plaza|bounty-bot|wholetrout|relayhop|misakanet|bountyscout|bounty-watch|scout|radar|frantic|splurt|go-hybrid|selftest|agent-bounty|dailydollar|project-a|nearportal|rustchain|bountee|paraloom|devloot|monetization|swarm", re.I)
JUNK_TEXT = re.compile(r"\bpoints?\b.{0,40}not money|reputation points|usdc|usdt|escrow|\bwallet\b|bounty seguro|airdrop|\$\s?wdoom|testnet|stake", re.I)
REPORT_ONLY = re.compile(r"\[bug bounty\]|security report|vulnerab", re.I)  # bug-report programs, not paid fixes
AMOUNT = re.compile(r"/bounty\s+\$?\s?([\d,]+)|\$\s?([\d,]{2,7})(?:\s?usd)?\b|\b([\d,]{2,7})\s?usd\b", re.I)


def api(path, params=None, method="GET", body=None):
    url = "https://api.github.com" + path
    if params:
        url += "?" + urllib.parse.urlencode(params, safe=":+><=\"")
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "bounty-watch")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and attempt < 2:
                time.sleep(20)
                continue
            print(f"API {e.code} on {path}", file=sys.stderr)
            return None
    return None


def search(q):
    time.sleep(2.5)  # stay under the search rate limit
    d = api("/search/issues", {"q": q, "sort": "created", "order": "desc", "per_page": 50})
    return (d or {}).get("items", [])


def amount_usd(text):
    best = 0
    for m in AMOUNT.finditer(text or ""):
        n = next(g for g in m.groups() if g)
        try:
            best = max(best, int(n.replace(",", "")))
        except ValueError:
            pass
    return best


def main():
    since = (datetime.now(timezone.utc) - timedelta(hours=HOURS_BACK)).strftime("%Y-%m-%dT%H:%M:%SZ")
    queries = [
        f"label:bounty is:issue is:open created:>={since}",
        f'label:"💎 Bounty" is:issue is:open created:>={since}',
        f'"/bounty" is:issue is:open created:>={since}',
    ]
    items = {}
    for q in queries:
        for i in search(q):
            items[i["html_url"]] = i

    already = set()
    if OWN_REPO and not DRY_RUN:
        for i in api(f"/repos/{OWN_REPO}/issues", {"state": "all", "per_page": 100}) or []:
            already.update(re.findall(r"https://github\.com/\S+/issues/\d+", i.get("body") or ""))

    hits = []
    for url, i in items.items():
        repo = i["repository_url"].split("/repos/")[1]
        text = f"{i['title']}\n{i.get('body') or ''}"
        if url in already or SPAM_REPO.search(repo) or JUNK_TEXT.search(text) or REPORT_ONLY.search(i["title"]):
            continue
        if i.get("assignee") or i["comments"] > MAX_COMMENTS or i.get("pull_request"):
            continue
        usd = amount_usd(text)
        if usd < MIN_USD and i["comments"]:
            comments = api(f"/repos/{repo}/issues/{i['number']}/comments", {"per_page": 30}) or []
            ctext = "\n".join(c.get("body") or "" for c in comments)
            if JUNK_TEXT.search(ctext) or re.search(r"/attempt", ctext):
                continue
            usd = max(usd, amount_usd(ctext))
        if usd < MIN_USD:
            continue
        r = api(f"/repos/{repo}") or {}
        if r.get("archived") or r.get("stargazers_count", 0) < MIN_STARS or r.get("language") not in LANGS:
            continue
        prs = search(f"is:pr is:open repo:{repo} {i['number']}")
        if prs:
            continue
        hits.append({"url": url, "repo": repo, "title": i["title"], "usd": usd,
                     "lang": r.get("language"), "stars": r.get("stargazers_count"),
                     "comments": i["comments"], "created": i["created_at"]})

    if not hits:
        print("NONE")
        return
    for h in hits:
        line = f"${h['usd']} | {h['repo']} ({h['lang']}, {h['stars']} stars) | {h['title']}"
        print(line)
        if DRY_RUN or not OWN_REPO:
            continue
        api(f"/repos/{OWN_REPO}/issues", method="POST", body={
            "title": f"Bounty: ${h['usd']} {h['repo']} - {h['title'][:70]}",
            "assignees": [OWNER],
            "body": (f"@{OWNER} new bounty, move fast.\n\n{h['url']}\n\nAmount: ${h['usd']}\n"
                     f"Language: {h['lang']} ({h['stars']} stars)\nComments so far: {h['comments']}\n"
                     f"Posted: {h['created']}\nOpen competing PRs: 0\n\n"
                     "Tell Claude: money making 2, then paste this link."),
        })


if __name__ == "__main__":
    main()
