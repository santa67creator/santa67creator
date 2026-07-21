import os
import sys
import re
import json
import glob
import urllib.request
from xml.sax.saxutils import escape

CARD_W = 340
CARD_H = 170

START_MARKER = "<!-- PINNED-PROJECTS:START -->"
END_MARKER = "<!-- PINNED-PROJECTS:END -->"

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
    with urllib.request.urlopen(req, timeout=30) as resp:
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
    if "errors" in data:
        print(data["errors"])
        sys.exit(1)
    return data["data"]["user"]["pinnedItems"]["nodes"]


def safe_filename(name):
    return re.sub(r"[^a-zA-Z0-9_-]", "-", name).lower()

def wrap_text(text, max_chars=46):
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

def render_card_svg(repo):
    name = repo["name"]
    description = repo.get("description") or ""
    lang = repo.get("primaryLanguage") or {}
    lang_name = lang.get("name", "Unknown")
    lang_color = lang.get("color") or "#8b949e"
    stars = repo.get("stargazerCount", 0)

    desc_lines = wrap_text(description)
    desc_svg = ""
    for i, line in enumerate(desc_lines):
        desc_svg += f'<text x="24" y="{78 + i * 20}" fill="#8b949e" font-size="13">{escape(line)}</text>\n'

    footer_y = 78 + len(desc_lines) * 20 + 14

    return f'''<svg viewBox="0 0 {CARD_W} {CARD_H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif">
  <rect x="1" y="1" width="{CARD_W - 2}" height="{CARD_H - 2}" rx="6" fill="#0d1117" stroke="#30363d"/>
  <g transform="translate(24,32) scale(0.9)">
    <path fill="#8b949e" d="M0 2a2 2 0 012-2h9.5a.25.25 0 01.25.25V5H14V.25A.25.25 0 0114.25 0H16a2 2 0 012 2v12.5a.25.25 0 01-.25.25h-1.5a.25.25 0 01-.25-.25V13H2v1.5a.25.25 0 01-.25.25H.25A.25.25 0 010 14.5V2z"/>
  </g>
  <text x="46" y="38" fill="#58a6ff" font-size="16" font-weight="600">{escape(name)}</text>
  {desc_svg}
  <circle cx="28" cy="{footer_y}" r="6" fill="{lang_color}"/>
  <text x="40" y="{footer_y + 5}" fill="#8b949e" font-size="12">{escape(lang_name)}</text>
  <text x="130" y="{footer_y + 5}" fill="#8b949e" font-size="12">&#9733; {stars}</text>
</svg>'''

def update_readme(readme_path, cards_markdown):
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    if START_MARKER not in content or END_MARKER not in content:
        print(f"::error::Could not find {START_MARKER} / {END_MARKER} markers in {readme_path}")
        sys.exit(1)

    pattern = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
    replacement = f"{START_MARKER}\n{cards_markdown}\n{END_MARKER}"
    new_content = pattern.sub(replacement, content)

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_card.py <username> <owner/repo>")
        sys.exit(1)
    username = sys.argv[1]
    repo_owner_repo = sys.argv[2]  # e.g. "santa67creator/santa67creator", where card svgs + README live
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("::error::GITHUB_TOKEN is not set.")
        sys.exit(1)
    
    repos = fetch_pinned(username, token)

    # remove stale card files from previous runs
    for f in glob.glob("card-*.svg"):
        os.remove(f)

    cards_md_parts = []
    for repo in repos:
        fname = f"card-{safe_filename(repo['name'])}.svg"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(render_card_svg(repo))
        raw_url = f"https://raw.githubusercontent.com/{repo_owner_repo}/main/{fname}"
        cards_md_parts.append(
            f'  <a href="{repo["url"]}"><img src="{raw_url}" width="340" /></a>'
        )

    cards_markdown = '<p align="center">\n' + "\n".join(cards_md_parts) + "\n</p>"
    update_readme("README.md", cards_markdown)
