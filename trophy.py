import os
import urllib.request
import json

USERNAME = os.getenv("USERNAME")
TOKEN = os.getenv("GITHUB_TOKEN")

query = """
{
  user(login: "%s") {
    followers {
      totalCount
    }
    repositories(ownerAffiliations: OWNER) {
      totalCount
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
    }
  }
}
""" % USERNAME

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": query}).encode(),
    headers={
        "Authorization": f"bearer {TOKEN}",
        "Content-Type": "application/json",
    },
)

data = json.loads(urllib.request.urlopen(req).read())

u = data["data"]["user"]

followers = u["followers"]["totalCount"]
repos = u["repositories"]["totalCount"]
commits = u["contributionsCollection"]["totalCommitContributions"]
prs = u["contributionsCollection"]["totalPullRequestContributions"]

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="260">
<rect width="100%" height="100%" fill="#0d1117"/>

<text x="450" y="45"
text-anchor="middle"
font-size="28"
fill="#58a6ff"
font-family="Segoe UI">
🏆 Trophy Cabinet
</text>

<text x="50" y="95" fill="white" font-size="20">💎 Commits: {commits}</text>
<text x="50" y="135" fill="white" font-size="20">🚀 Pull Requests: {prs}</text>
<text x="50" y="175" fill="white" font-size="20">📦 Repositories: {repos}</text>
<text x="50" y="215" fill="white" font-size="20">👥 Followers: {followers}</text>

</svg>
"""

with open("trophy.svg", "w", encoding="utf-8") as f:
    f.write(svg)
