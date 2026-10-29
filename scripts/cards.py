"""Gera profile/stats.svg e profile/top-langs.svg direto da API do GitHub.

Roda no GitHub Actions com o GITHUB_TOKEN; não depende de nenhum serviço externo.
Uso: GITHUB_TOKEN=... python scripts/cards.py <usuario>
     python scripts/cards.py <usuario> --mock dados.json   (só renderiza, para testar)
"""

import json
import os
import sys
import urllib.request
from html import escape
from pathlib import Path

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalIssueContributions
    }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST]) { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

BG = "#0d1117"
TEXT = "#c9d1d9"
MUTED = "#8b949e"
ACCENT = "#58a6ff"
FONT = "font-family:'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif"


def fetch(login: str) -> dict:
    token = os.environ["GITHUB_TOKEN"]
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise SystemExit(f"Erro da API: {data['errors']}")
    return data["data"]["user"]


def stats_svg(user: dict) -> str:
    c = user["contributionsCollection"]
    repos = user["repositories"]
    rows = [
        ("⭐", "Estrelas recebidas", sum(r["stargazerCount"] for r in repos["nodes"])),
        ("📝", "Commits no último ano", c["totalCommitContributions"] + c["restrictedContributionsCount"]),
        ("🔀", "Pull requests", c["totalPullRequestContributions"]),
        ("🐞", "Issues", c["totalIssueContributions"]),
        ("📦", "Repositórios públicos", repos["totalCount"]),
        ("🤝", "Contribuiu em (último ano)", user["repositoriesContributedTo"]["totalCount"]),
    ]
    lines = []
    for i, (icon, label, value) in enumerate(rows):
        y = 70 + i * 26
        lines.append(
            f'<text x="25" y="{y}" fill="{TEXT}" font-size="14">{icon}  {escape(label)}:</text>'
            f'<text x="330" y="{y}" fill="{TEXT}" font-size="14" font-weight="700" text-anchor="end">{value}</text>'
        )
    title = escape(f"Estatísticas de {user['name'] or 'GitHub'}")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="360" height="230" viewBox="0 0 360 230" style="{FONT}">
  <rect width="360" height="230" rx="6" fill="{BG}"/>
  <text x="25" y="35" fill="{ACCENT}" font-size="18" font-weight="600">{title}</text>
  {''.join(lines)}
</svg>
"""


def langs_svg(user: dict, top: int = 6) -> str:
    totals: dict[str, list] = {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name, color = edge["node"]["name"], edge["node"]["color"] or MUTED
            totals.setdefault(name, [0, color])[0] += edge["size"]
    ranked = sorted(totals.items(), key=lambda kv: kv[1][0], reverse=True)[:top]
    total = sum(size for _, (size, _) in ranked) or 1

    bar, x = [], 25.0
    for _, (size, color) in ranked:
        w = 310 * size / total
        bar.append(f'<rect x="{x:.2f}" y="50" width="{w:.2f}" height="8" fill="{color}"/>')
        x += w

    items = []
    for i, (name, (size, color)) in enumerate(ranked):
        cx, cy = 25 + (i % 2) * 160, 85 + (i // 2) * 24
        items.append(
            f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{color}"/>'
            f'<text x="{cx + 16}" y="{cy}" fill="{TEXT}" font-size="12">{escape(name)} {100 * size / total:.1f}%</text>'
        )
    height = 85 + ((len(ranked) + 1) // 2) * 24
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="360" height="{height}" viewBox="0 0 360 {height}" style="{FONT}">
  <rect width="360" height="{height}" rx="6" fill="{BG}"/>
  <text x="25" y="35" fill="{ACCENT}" font-size="18" font-weight="600">Linguagens mais usadas</text>
  <clipPath id="bar"><rect x="25" y="50" width="310" height="8" rx="4"/></clipPath>
  <g clip-path="url(#bar)">{''.join(bar)}</g>
  {''.join(items)}
</svg>
"""


def main() -> None:
    login = sys.argv[1]
    if "--mock" in sys.argv:
        user = json.loads(Path(sys.argv[sys.argv.index("--mock") + 1]).read_text())
    else:
        user = fetch(login)
    out = Path("profile")
    out.mkdir(exist_ok=True)
    (out / "stats.svg").write_text(stats_svg(user), encoding="utf-8")
    (out / "top-langs.svg").write_text(langs_svg(user), encoding="utf-8")
    print("Cards gerados em profile/")


if __name__ == "__main__":
    main()
