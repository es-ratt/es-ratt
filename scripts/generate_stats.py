#!/usr/bin/env python3
"""Builds assets/stats.svg and assets/languages.svg straight from the GitHub API.

Usage:
    python3 scripts/generate_stats.py             # user = $GITHUB_REPOSITORY_OWNER (set automatically in Actions)
    python3 scripts/generate_stats.py YOUR_NAME   # a specific user
    python3 scripts/generate_stats.py --sample    # placeholder numbers, no API call
"""
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
API = "https://api.github.com"
W, H = 380, 170
BAR_COLORS = ["#ff6f9d", "#7fe8c0", "#ffa3c1", "#c9a7ff", "#ffd08a"]

SAMPLE = {
    "repos": 7, "stars": 0, "followers": 0, "following": 0,
    "langs": {"C++": 40, "Python": 30, "Java": 20, "HTML": 10},
}


def api(path: str):
    req = urllib.request.Request(
        API + path,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-stats-cards"},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def collect(user: str) -> dict:
    profile = api(f"/users/{user}")

    repos, page = [], 1
    while True:
        chunk = api(f"/users/{user}/repos?per_page=100&type=owner&page={page}")
        repos += chunk
        if len(chunk) < 100:
            break
        page += 1

    own = [r for r in repos if not r.get("fork")]
    stars = sum(r.get("stargazers_count", 0) for r in own)

    langs: dict[str, int] = {}
    for r in sorted(own, key=lambda r: r.get("pushed_at") or "", reverse=True)[:50]:
        try:
            data = api(f"/repos/{user}/{r['name']}/languages")
        except Exception:
            data = {r["language"]: 1} if r.get("language") else {}
        for name, size in data.items():
            langs[name] = langs.get(name, 0) + size

    return {
        "repos": profile["public_repos"],
        "stars": stars,
        "followers": profile["followers"],
        "following": profile["following"],
        "langs": langs,
    }


def card(title: str, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{escape(title)}">
  <title>{escape(title)}</title>
  <style>text {{ font-family: "JetBrains Mono", "Fira Code", Consolas, "SF Mono", "Courier New", monospace; }}</style>
  <defs>
    <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
      <path d="M20 0H0V20" fill="none" stroke="#fff" stroke-opacity=".035"/>
    </pattern>
  </defs>
  <rect width="{W}" height="{H}" fill="#0a090d"/>
  <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" fill="url(#grid)" stroke="#2b2733"/>
  <rect x="20" y="20" width="8" height="8" fill="#ff6f9d" shape-rendering="crispEdges"/>
  <text x="36" y="28" font-size="15" font-weight="700" fill="#ff8fb1">{escape(title)}</text>
{body}
</svg>
'''


def stats_svg(d: dict) -> str:
    rows = [
        ("public repos", d["repos"]),
        ("stars earned", d["stars"]),
        ("followers", d["followers"]),
        ("following", d["following"]),
    ]
    out = []
    for i, (label, value) in enumerate(rows):
        y = 66 + i * 26
        out.append(f'  <text x="20" y="{y}" font-size="13" fill="#f6c9d8">{label}</text>')
        out.append(f'  <text x="{W - 20}" y="{y}" text-anchor="end" font-size="16" font-weight="700" fill="#7fe8c0">{value}</text>')
        if i < len(rows) - 1:
            out.append(f'  <rect x="20" y="{y + 9}" width="{W - 40}" height="1" fill="#2b2733"/>')
    return card("github stats", "\n".join(out))


def languages_svg(d: dict) -> str:
    langs = d["langs"]
    total = sum(langs.values())
    if not total:
        body = '  <text x="20" y="70" font-size="13" fill="#8a8592">no language data yet</text>'
        return card("top languages", body)

    top = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:5]
    track_x, track_w = 130, 170
    out = []
    for i, (name, size) in enumerate(top):
        y = 62 + i * 22
        pct = size * 100 / total
        bar = max(4, round(track_w * pct / 100))
        color = BAR_COLORS[i % len(BAR_COLORS)]
        out.append(f'  <text x="20" y="{y}" font-size="13" fill="#f6c9d8">{escape(name[:12])}</text>')
        out.append(f'  <rect x="{track_x}" y="{y - 10}" width="{track_w}" height="10" fill="#2b0f1f" shape-rendering="crispEdges"/>')
        out.append(f'  <rect x="{track_x}" y="{y - 10}" width="{bar}" height="10" fill="{color}" shape-rendering="crispEdges"/>')
        out.append(f'  <text x="{W - 20}" y="{y}" text-anchor="end" font-size="12" fill="#8a8592">{pct:.0f}%</text>')
    return card("top languages", "\n".join(out))


def main() -> None:
    args = sys.argv[1:]
    if "--sample" in args:
        data = SAMPLE
    else:
        user = args[0] if args else os.environ.get("GITHUB_REPOSITORY_OWNER")
        if not user:
            sys.exit("Pass a GitHub username or set GITHUB_REPOSITORY_OWNER.")
        data = collect(user)

    for name, svg in (("stats.svg", stats_svg(data)), ("languages.svg", languages_svg(data))):
        path = os.path.join(ASSETS, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        print("wrote", os.path.normpath(path))


if __name__ == "__main__":
    main()
