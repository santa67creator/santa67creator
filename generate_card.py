import os
import sys
import json
import urllib.request
from xml.sax.saxutils import escape

LANG_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "C++": "#f34b7d",
    "C": "#555555",
    "Assembly": "#6E4C13",
    "Shell": "#89e051",
    "Dockerfile": "#384d54",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Rust": "#dea584",
    "Go": "#00ADD8",
}

def fetch_repo(full_name, token):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{full_name}",
        headers={
            "Authorization": f"token {token}",
            "User-Agent": "profile-readme-card-generator",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def wrap_text(text, max_chars=54):
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

def build_card(repo_full_name, display_name, token):
    data = fetch_repo(repo_full_name, token)
    description = data.get("description") or ""
    language = data.get("language") or "Unknown"
    stars = data.get("stargazers_count", 0)
    color = LANG_COLORS.get(language, "#8b949e")

    desc_lines = wrap_text(description, 50)
    desc_svg = ""
    for i, line in enumerate(desc_lines):
        desc_svg += f'<text x="24" y="{78 + i * 20}" fill="#8b949e" font-size="13">{escape(line)}</text>\n'

    svg = f'''<svg viewBox="0 0 340 170" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif">
  <rect x="1" y="1" width="338" height="168" rx="6" fill="#0d1117" stroke="#30363d"/>
  <g transform="translate(24,32)">
    <path fill="#8b949e" d="M0 2a2 2 0 012-2h9.5a.25.25 0 01.25.25V5H14V.25A.25.25 0 0114.25 0H16a2 2 0 012 2v12.5a.25.25 0 01-.25.25h-1.5a.25.25 0 01-.25-.25V13H2v1.5a.25.25 0 01-.25.25H.25A.25.25 0 010 14.5V2z" transform="scale(0.9)"/>
  </g>
  <text x="46" y="38" fill="#58a6ff" font-size="16" font-weight="600">{escape(display_name)}</text>
  {desc_svg}
  <circle cx="28" cy="{78 + len(desc_lines) * 20 + 14}" r="6" fill="{color}"/>
  <text x="40" y="{78 + len(desc_lines) * 20 + 19}" fill="#8b949e" font-size="12">{escape(language)}</text>
  <text x="120" y="{78 + len(desc_lines) * 20 + 19}" fill="#8b949e" font-size="12">&#9733; {stars}</text>
</svg>'''
    return svg

if __name__ == "__main__":
    repo_full_name = sys.argv[1]
    display_name = sys.argv[2]
    token = os.environ["GITHUB_TOKEN"]
    print(build_card(repo_full_name, display_name, token))
