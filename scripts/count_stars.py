"""Write badges/stars.json, the shields.io endpoint behind the "stars on my repos" badge.

shields.io stopped taking the `affiliations` parameter, so its own GitHub stars badge can no longer add an
organisation's repositories to a user's. This counts them from the public API instead: every public repository,
forks left out, of each account in OWNERS. Any failure exits non-zero and writes nothing, so the badge keeps its
last good number rather than a wrong one.

    python3 scripts/count_stars.py            # print the total and write the badge file
    python3 scripts/count_stars.py --dry-run  # print the total and the repositories only
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

OWNERS = [("users", "vladimirrott"), ("orgs", "lacs-project"), ("orgs", "loopgepa")]
OUT = Path(__file__).resolve().parents[1] / "badges" / "stars.json"


def get(url: str) -> tuple[list, str | None]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "vladimirrott-profile-stars"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        link = response.headers.get("Link") or ""
        nxt = re.search(r'<([^>]+)>;\s*rel="next"', link)
        return json.loads(response.read()), nxt.group(1) if nxt else None


def repositories(kind: str, name: str) -> list[dict]:
    kind_filter = "owner" if kind == "users" else "public"
    url: str | None = f"https://api.github.com/{kind}/{name}/repos?per_page=100&type={kind_filter}"
    out: list[dict] = []
    while url:
        page, url = get(url)
        out += page
    return [r for r in out if not r["fork"] and not r["private"]]


def main(argv: list[str]) -> int:
    counted = []
    for kind, name in OWNERS:
        repos = repositories(kind, name)
        if not repos:
            print(f"!! {name} returned no public repositories; refusing to write a total", file=sys.stderr)
            return 1
        counted += repos
    total = sum(r["stargazers_count"] for r in counted)
    for r in sorted(counted, key=lambda r: -r["stargazers_count"]):
        print(f"{r['stargazers_count']:5} {r['full_name']}")
    print(f"total {total}")
    if "--dry-run" not in argv:
        badge = {"schemaVersion": 1, "label": "stars on my repos", "message": str(total), "color": "blue",
                 "namedLogo": "github", "style": "flat-square", "cacheSeconds": 3600}
        OUT.write_text(json.dumps(badge, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
