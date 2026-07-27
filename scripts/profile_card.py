"""
Rendert einen Steckbrief im Neofetch-Stil als animiertes SVG.

Die persoenlichen Zeilen stehen unten in INFO, die GitHub-Zahlen kommen
live ueber die API. Zeilen faden nacheinander ein, wie ein Terminal,
das sich aufbaut.

Env: GITHUB_TOKEN, GH_LOGIN
Ausgabe: dist/profile-card.svg
"""

import json
import os
import urllib.request

# --- Layout ---
CHAR_W = 7.8       # Zeichenbreite bei 13px Monospace, fuer die Spaltenmathematik
LINE_H = 19
FONT = 13
COLS = 60          # Zeichenbreite der rechten Spalte inkl. Punktfuehrung
ART_X = 26
INFO_X = 250
TOP = 34
STAGGER = 0.055    # Versatz pro Zeile beim Einfaden

# --- Farben (Terminal auf GitHub-Dark) ---
BG = "#0d1117"
BORDER = "#30363d"
LABEL = "#58a6ff"
VALUE = "#c9d1d9"
DIM = "#30363d"     # Punkte der Fuehrungslinie
HEAD = "#8b949e"    # Sektionsueberschriften
ART = "#58a6ff"
GREEN = "#3fb950"

ART_LINES = [
    r"  _  _    ___  _  _  ",
    r" | || |  / _ \| || | ",
    r" | || |_| | | | || |_",
    r" |__   _| |_| |__   _|",
    r"    |_|  \___/   |_| ",
    r"",
    r"  > codux404",
    r"  > status: learning",
]

QUERY = """
query($login: String!) {
  user(login: $login) {
    login
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC) {
      totalCount
      nodes { stargazerCount }
    }
    contributionsCollection { totalCommitContributions }
  }
}
"""


def fetch_stats(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": login,
        },
    )
    with urllib.request.urlopen(req) as resp:
        payload = json.load(resp)

    if "errors" in payload:
        raise RuntimeError(payload["errors"])

    user = payload["data"]["user"]
    return {
        "repos": user["repositories"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in user["repositories"]["nodes"]),
        "followers": user["followers"]["totalCount"],
        "commits": user["contributionsCollection"]["totalCommitContributions"],
    }


def info_lines(stats):
    """Aufbau des Steckbriefs. Hier anpassen, nichts weiter."""
    return [
        ("head", "codux404@github"),
        ("row", "Status", "Dual student, B.Sc. Computer Science"),
        ("row", "Mode", "University / industry, alternating"),
        ("row", "Company", "Mechanical engineering, software side"),
        ("blank", ""),
        ("sec", "Languages"),
        ("row", "Programming", "Java, C, C++"),
        ("row", "Markup", "LaTeX, Markdown"),
        ("row", "Spoken", "German, English"),
        ("blank", ""),
        ("sec", "Environment"),
        ("row", "Editors", "VS Code, Visual Studio, Arduino IDE"),
        ("row", "Currently", "C fundamentals, ESP32 sensor rig"),
        ("blank", ""),
        ("sec", "GitHub"),
        ("row", "Repos", str(stats["repos"])),
        ("row", "Stars", str(stats["stars"])),
        ("row", "Followers", str(stats["followers"])),
        ("row", "Commits", f"{stats['commits']} in the last year"),
        ("blank", ""),
        ("sec", "Contact"),
        ("row", "Email", "YOUR@MAIL.COM"),
        ("row", "LinkedIn", "YOUR_LINKEDIN"),
    ]


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(stats):
    lines = info_lines(stats)
    rows = max(len(lines), len(ART_LINES))
    width = INFO_X + COLS * CHAR_W + 26
    height = TOP + rows * LINE_H + 22

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}">',
        "<style>",
        f"text{{font-family:ui-monospace,'SF Mono','Cascadia Mono','Segoe UI Mono',"
        f"'JetBrains Mono',Consolas,monospace;font-size:{FONT}px;white-space:pre}}",
        f".l{{opacity:0;animation:in .3s ease-out forwards}}",
        "@keyframes in{to{opacity:1}}",
        "</style>",
        f'<rect width="{width:.0f}" height="{height:.0f}" rx="8" fill="{BG}" '
        f'stroke="{BORDER}" stroke-width="1"/>',
    ]

    # ASCII-Art, vertikal zentriert
    art_top = TOP + (rows - len(ART_LINES)) * LINE_H / 2
    for i, line in enumerate(ART_LINES):
        y = art_top + i * LINE_H
        delay = round(i * STAGGER, 3)
        out.append(
            f'<text class="l" x="{ART_X}" y="{y:.0f}" fill="{ART}" '
            f'style="animation-delay:{delay}s" xml:space="preserve">{esc(line)}</text>'
        )

    for i, entry in enumerate(lines):
        kind = entry[0]
        y = TOP + i * LINE_H
        delay = round(i * STAGGER, 3)
        style = f'style="animation-delay:{delay}s"'

        if kind == "blank":
            continue

        if kind == "head":
            text = entry[1]
            rule = "─" * (COLS - len(text) - 1)
            out.append(
                f'<text class="l" x="{INFO_X}" y="{y}" {style} xml:space="preserve">'
                f'<tspan fill="{VALUE}">{esc(text)}</tspan>'
                f'<tspan fill="{DIM}"> {rule}</tspan></text>'
            )
        elif kind == "sec":
            text = entry[1]
            rule = "─" * (COLS - len(text) - 4)
            out.append(
                f'<text class="l" x="{INFO_X}" y="{y}" {style} xml:space="preserve">'
                f'<tspan fill="{DIM}">─ </tspan>'
                f'<tspan fill="{HEAD}">{esc(text)}</tspan>'
                f'<tspan fill="{DIM}"> {rule}</tspan></text>'
            )
        else:
            label, value = entry[1], entry[2]
            # Punkte auffuellen, damit die Werte rechtsbuendig stehen
            dots = "." * max(2, COLS - len(label) - len(value) - 3)
            color = GREEN if label in ("Stars", "Followers") else VALUE
            out.append(
                f'<text class="l" x="{INFO_X}" y="{y}" {style} xml:space="preserve">'
                f'<tspan fill="{LABEL}">{esc(label)}:</tspan>'
                f'<tspan fill="{DIM}"> {dots} </tspan>'
                f'<tspan fill="{color}">{esc(value)}</tspan></text>'
            )

    out.append("</svg>")
    return "\n".join(out)


def main():
    login = os.environ["GH_LOGIN"]
    token = os.environ["GITHUB_TOKEN"]
    stats = fetch_stats(login, token)

    os.makedirs("dist", exist_ok=True)
    with open("dist/profile-card.svg", "w") as f:
        f.write(render(stats))
    print("wrote profile-card.svg")


if __name__ == "__main__":
    main()
