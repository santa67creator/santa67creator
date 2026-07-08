import os
import sys
import json
import urllib.request
from xml.sax.saxutils import escape

CARD_W = 340
CARD_H = 170
GAP = 20
COLS = 2

def graphql(query, token):
    body = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "User-Agent": "profile-readme-card-generator",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def fetch_pinned(username, token):
    query = f'''
    {{
      user(login: "{username}") {{
        pinnedItems(first: 6, types: [REPOSITORY]) {{
          nodes {{
            ... on Repository {{
              name
              url
              description
              stargazerCount
              primaryLanguage {{ name color }}
            }}
          }}
        }}
      }}
    }}
    '''
    data = graphql(query, token)
    return data["data"]["user"]["pinnedItems"]["nodes"]

def wrap_text(text, max_chars=50):
    words = text.split()
    lines, current = [], ""
    for w in words:
        if len(current) + len(w) + 1 <= max_chars:
            current = (current + " " + w).strip()
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines[:2]

def render_card(repo, x, y):
    name = repo["name"]
    description = repo.get("description") or ""
    lang = repo.get("primaryLanguage") or {}
    lang_name = lang.get("name", "Unknown")
    lang_color = lang.get("color") or "#8b949e"
    stars = repo.get("stargazerCount", 0)

    desc_lines = wrap_text(description, 46)
    desc_svg = ""
    for i, line in enumerate(desc_lines):
        desc_svg += f'<text x="24" y="{78 + i * 20}" fill="#8b949e" font-size="13">{escape(line)}</text>\n'

    footer_y = 78 + len(desc_lines) * 20 + 14

    return f'''
  <g transform="translate({x},{y})">
    <rect x="1" y="1" width="{CARD_W - 2}" height="{CARD_H - 2}" rx="6" fill="#0d1117" stroke="#30363d"/>
    <g transform="translate(24,32) scale(0.9)">
      <path fill="#8b949e" d="M0 2a2 2 0 012-2h9.5a.25.25 0 01.25.25V5H14V.25A.25.25 0 0114.25 0H16a2 2 0 012 2v12.5a.25.25 0 01-.25.25h-1.5a.25.25 0 01-.25-.25V13H2v1.5a.25.25 0 01-.25.25H.25A.25.25 0 010 14.5V2z"/>
    </g>
    <text x="46" y="38" fill="#58a6ff" font-size="16" font-weight="600">{escape(name)}</text>
    {desc_svg}
    <circle cx="28" cy="{footer_y}" r="6" fill="{lang_color}"/>
    <text x="40" y="{footer_y + 5}" fill="#8b949e" font-size="12">{escape(lang_name)}</text>
    <text x="130" y="{footer_y + 5}" fill="#8b949e" font-size="12">&#9733; {stars}</text>
  </g>'''

def build_svg(repos):
    rows = (len(repos) + COLS - 1) // COLS
    total_w = COLS * CARD_W + (COLS - 1) * GAP
    total_h = rows * CARD_H + (rows - 1) * GAP

    cards = ""
    for i, repo in enumerate(repos):
        col = i % COLS
        row = i // COLS
        x = col * (CARD_W + GAP)
        y = row * (CARD_H + GAP)
        cards += render_card(repo, x, y)

    return f'''<svg viewBox="0 0 {total_w} {total_h}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif">
{cards}
</svg>'''

if __name__ == "__main__":
    username = sys.argv[1]
    token = os.environ["GITHUB_TOKEN"]
    repos = fetch_pinned(username, token)
    print(build_svg(repos))
