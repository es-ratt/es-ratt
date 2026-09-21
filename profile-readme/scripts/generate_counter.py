#!/usr/bin/env python3
"""Builds assets/repo-counter.svg: an SVG whose number counts 1 -> N (your public repo count) on loop.

Usage:
    python3 scripts/generate_counter.py              # user = $GITHUB_REPOSITORY_OWNER (set automatically in Actions)
    python3 scripts/generate_counter.py YOUR_NAME    # fetch count for a specific user
    python3 scripts/generate_counter.py --count 12   # skip the API and use a fixed number (for testing)
"""
import json
import math
import os
import sys
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "repo-counter.svg")

CYCLE = 8.0        # seconds per loop
COUNT_TIME = 2.4   # seconds spent counting up; the rest of the loop holds the final number
MAX_FRAMES = 40    # cap so big accounts don't create a huge SVG


def fetch_count(user: str) -> int:
    req = urllib.request.Request(
        f"https://api.github.com/users/{user}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-repo-counter"},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return int(json.load(resp)["public_repos"])


def frames_for(n: int) -> list[int]:
    if n <= 1:
        return [max(n, 0)]
    step = math.ceil(n / MAX_FRAMES)
    nums = list(range(1, n + 1, step))
    if nums[-1] != n:
        nums.append(n)
    return nums


def number_nodes(nums: list[int]) -> str:
    attrs = 'x="330" y="80" text-anchor="end" font-size="54" font-weight="700" fill="#ff6f9d"'
    if len(nums) == 1:
        return f'<text {attrs}>{nums[0]}</text>'

    c = COUNT_TIME / CYCLE
    f = len(nums)
    out = []
    for i, num in enumerate(nums):
        a = i * c / f
        b = (i + 1) * c / f
        last = i == f - 1
        if i == 0:
            values, keys = "1;0;0", f"0;{b:.5f};1"
        elif last:
            values, keys = "0;1;1", f"0;{a:.5f};1"
        else:
            values, keys = "0;1;0;0", f"0;{a:.5f};{b:.5f};1"
        # the last frame is visible by default so non-animating viewers still see the real number
        base = 1 if last else 0
        out.append(
            f'<text {attrs} opacity="{base}">{num}'
            f'<animate attributeName="opacity" calcMode="discrete" dur="{CYCLE}s" '
            f'repeatCount="indefinite" values="{values}" keyTimes="{keys}"/></text>'
        )
    return "\n    ".join(out)


def build_svg(n: int) -> str:
    nodes = number_nodes(frames_for(n))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 110" width="360" height="110" role="img" aria-label="Public repositories: {n}">
  <title>Public repositories: {n}</title>
  <style>
    text {{ font-family: "JetBrains Mono", "Fira Code", Consolas, "SF Mono", "Courier New", monospace; }}
    .live {{ animation: blink 1.4s steps(1) infinite; }}
    @keyframes blink {{ 50% {{ opacity: 0; }} }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
  </style>
  <defs>
    <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
      <path d="M20 0H0V20" fill="none" stroke="#fff" stroke-opacity=".035"/>
    </pattern>
  </defs>
  <rect width="360" height="110" fill="#0a090d"/>
  <rect x=".5" y=".5" width="359" height="109" fill="url(#grid)" stroke="#2b2733"/>

  <!-- pixel folder -->
  <g shape-rendering="crispEdges">
    <rect x="28" y="34" width="20" height="8" fill="#ff6f9d"/>
    <rect x="28" y="42" width="48" height="34" fill="#ff6f9d"/>
    <rect x="34" y="50" width="36" height="20" fill="#2b0f1f"/>
    <rect x="40" y="56" width="12" height="4" fill="#ffa3c1"/>
    <rect x="40" y="62" width="20" height="4" fill="#ffa3c1"/>
  </g>

  <text x="92" y="58" font-size="18" fill="#f6c9d8">repos</text>
  <text x="92" y="78" font-size="11" fill="#8a8592">public, counted live</text>

  <rect class="live" x="290" y="17" width="7" height="7" fill="#7fe8c0"/>
  <text x="332" y="24" text-anchor="end" font-size="11" fill="#7fe8c0">live</text>

  <g>
    {nodes}
  </g>
</svg>
'''


def main() -> None:
    args = sys.argv[1:]
    if args[:1] == ["--count"] and len(args) >= 2:
        n = int(args[1])
    else:
        user = args[0] if args else os.environ.get("GITHUB_REPOSITORY_OWNER")
        if not user:
            sys.exit("Pass a GitHub username or set GITHUB_REPOSITORY_OWNER.")
        n = fetch_count(user)

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(build_svg(n))
    print(f"wrote {os.path.normpath(OUT)} with {n} repos")


if __name__ == "__main__":
    main()
