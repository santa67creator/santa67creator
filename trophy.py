import os
import sys
import json
import datetime
import urllib.request
import urllib.error

USERNAME = os.getenv("USERNAME")
TOKEN = os.getenv("GITHUB_TOKEN")

if not USERNAME or not TOKEN:
    print("::error::USERNAME and GITHUB_TOKEN environment variables are required.")
    sys.exit(1)

API_URL = "https://api.github.com/graphql"

# ---------------------------------------------------------------------------
# GraphQL helpers
# ---------------------------------------------------------------------------

def graphql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "profile-trophy-cabinet",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"::error::GitHub API request failed: {e.code} {e.read().decode()}")
        sys.exit(1)
    if "errors" in data:
        print(f"::error::GraphQL errors: {data['errors']}")
        sys.exit(1)
    return data["data"]


MAIN_QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { stargazerCount }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
      }
    }
  }
}
"""


def fetch_user_data(login):
    followers = 0
    repos_total = 0
    stars_total = 0
    cursor = None
    contributions = None
    created_at = None

    while True:
        data = graphql(MAIN_QUERY, {"login": login, "cursor": cursor})
        u = data["user"]
        created_at = u["createdAt"]
        followers = u["followers"]["totalCount"]
        repos_total = u["repositories"]["totalCount"]
        stars_total += sum(n["stargazerCount"] for n in u["repositories"]["nodes"])
        if contributions is None:
            contributions = u["contributionsCollection"]

        page_info = u["repositories"]["pageInfo"]
        if page_info["hasNextPage"]:
            cursor = page_info["endCursor"]
        else:
            break

    return {
        "followers": followers,
        "repos": repos_total,
        "stars": stars_total,
        "commits": contributions["totalCommitContributions"],
        "prs": contributions["totalPullRequestContributions"],
        "issues": contributions["totalIssueContributions"],
        "contrib_total": contributions["contributionCalendar"]["totalContributions"],
        "created_at": created_at,
    }


def experience(created_at_iso):
    """Return (years_as_float, display_string) describing account age."""
    created = datetime.datetime.strptime(created_at_iso, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc
    )
    now = datetime.datetime.now(datetime.timezone.utc)
    days = (now - created).days
    years, remainder_days = divmod(days, 365)
    months = remainder_days // 30

    if years == 0 and months == 0:
        display = "New"
    elif years == 0:
        display = f"{months}mo"
    elif months == 0:
        display = f"{years}y"
    else:
        display = f"{years}y {months}mo"

    return days / 365.0, display


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

BG = "#0d1117"
TILE_BG = "#161b22"
BORDER = "#30363d"
TEXT_MAIN = "#f0f6fc"
TEXT_MUTED = "#8b949e"
ACCENT = "#58a6ff"

TIERS = [
    ("—",         "#6e7681"),
    ("Bronze",    "#cd7f32"),
    ("Silver",    "#a9b1bb"),
    ("Gold",      "#ffd54a"),
    ("Platinum",  "#79dfff"),
    ("Legendary", "#d29bff"),
]


def get_tier(value, thresholds):
    idx = 0
    for i, t in enumerate(thresholds):
        if value >= t:
            idx = i + 1
    return TIERS[idx]


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


COLS = 4
CARD_W = 900
PAD = 28
GAP = 14
TILE_W = (CARD_W - PAD * 2 - GAP * (COLS - 1)) / COLS
TILE_H = 118
HEADER_H = 74


def render_tile(x, y, icon, label, value_str, tier_name, tier_color):
    tier_label = tier_name.upper()
    badge_w = 16 + len(tier_label) * 5.6
    badge_x = TILE_W - 14 - badge_w
    return f'''
  <g transform="translate({x},{y})">
    <rect width="{TILE_W}" height="{TILE_H}" rx="10" fill="{TILE_BG}" stroke="{tier_color}" stroke-opacity="0.55" stroke-width="1.3"/>
    <rect x="0" y="0" width="4" height="{TILE_H}" rx="2" fill="{tier_color}"/>
    <text x="18" y="31" font-size="19">{icon}</text>
    <rect x="{badge_x:.1f}" y="12" width="{badge_w:.1f}" height="16" rx="8" fill="{tier_color}" fill-opacity="0.16" stroke="{tier_color}" stroke-opacity="0.6" stroke-width="0.8"/>
    <text x="{badge_x + badge_w/2:.1f}" y="23.5" text-anchor="middle" font-size="9" font-weight="700" letter-spacing="0.4" fill="{tier_color}">{tier_label}</text>
    <text x="18" y="68" font-size="28" font-weight="700" fill="{TEXT_MAIN}" font-family="Segoe UI, Helvetica, Arial, sans-serif">{esc(value_str)}</text>
    <text x="18" y="92" font-size="12" fill="{TEXT_MUTED}" letter-spacing="0.3">{esc(label)}</text>
  </g>'''


def build_svg(username, stats):
    exp_years, exp_display = experience(stats["created_at"])

    entries = [
        ("💎", "Commits · 1y",       f'{stats["commits"]:,}',       stats["commits"],       [1, 50, 200, 500, 1000]),
        ("🚀", "Pull Requests · 1y", f'{stats["prs"]:,}',           stats["prs"],           [1, 10, 30, 75, 150]),
        ("🐛", "Issues Opened · 1y", f'{stats["issues"]:,}',        stats["issues"],        [1, 5, 15, 40, 80]),
        ("⭐", "Stars Earned",       f'{stats["stars"]:,}',         stats["stars"],         [1, 10, 50, 150, 400]),
        ("👥", "Followers",         f'{stats["followers"]:,}',     stats["followers"],     [1, 10, 50, 150, 400]),
        ("📦", "Repositories",      f'{stats["repos"]:,}',         stats["repos"],         [1, 5, 15, 30, 60]),
        ("📈", "Contributions · 1y",f'{stats["contrib_total"]:,}', stats["contrib_total"], [1, 200, 500, 1000, 2000]),
        ("⏳", "Experience",        exp_display,                    exp_years,               [0.25, 1, 2, 4, 7]),
    ]

    rows = (len(entries) + COLS - 1) // COLS
    card_h = HEADER_H + PAD + rows * TILE_H + (rows - 1) * GAP + PAD

    tiles_svg = ""
    for i, (icon, label, value_str, rank_value, thresholds) in enumerate(entries):
        row = i // COLS
        col = i % COLS
        x = PAD + col * (TILE_W + GAP)
        y = HEADER_H + PAD + row * (TILE_H + GAP)
        tier_name, tier_color = get_tier(rank_value, thresholds)
        tiles_svg += render_tile(x, y, icon, label, value_str, tier_name, tier_color)

    return f'''<svg width="{CARD_W}" height="{card_h}" viewBox="0 0 {CARD_W} {card_h}" xmlns="http://www.w3.org/2000/svg"
     font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif">
  <rect x="0.5" y="0.5" width="{CARD_W-1}" height="{card_h-1}" rx="10" fill="{BG}" stroke="{BORDER}"/>
  <text x="{CARD_W/2}" y="34" text-anchor="middle" font-size="22" font-weight="700" fill="{ACCENT}">🏆 Trophy Cabinet</text>
  <text x="{CARD_W/2}" y="54" text-anchor="middle" font-size="12.5" fill="{TEXT_MUTED}">@{esc(username)}</text>
  <line x1="{PAD}" y1="{HEADER_H - 4}" x2="{CARD_W - PAD}" y2="{HEADER_H - 4}" stroke="{BORDER}" stroke-width="1"/>
  {tiles_svg}
</svg>'''


if __name__ == "__main__":
    data = fetch_user_data(USERNAME)
    svg = build_svg(USERNAME, data)
    with open("trophy.svg", "w", encoding="utf-8") as f:
        f.write(svg)
