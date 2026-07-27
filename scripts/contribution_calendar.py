"""
Rendert den GitHub-Contribution-Kalender als animiertes SVG im Original-Stil.

Laeuft in GitHub Actions, braucht nur die Standardbibliothek.
Env: GITHUB_TOKEN (vom Workflow gestellt), GH_LOGIN (dein Username)
Ausgabe: dist/contributions.svg (light) und dist/contributions-dark.svg
"""

import json
import os
import urllib.request

# --- Layout (entspricht GitHubs eigenem Raster) ---
CELL = 11          # Kantenlaenge einer Zelle
GAP = 3            # Abstand zwischen Zellen
RADIUS = 2         # Eckenrundung
PITCH = CELL + GAP # Rasterabstand
PAD = 12           # Aussenrand
LABEL_LEFT = 30    # Platz fuer Mo/Mi/Fr
LABEL_TOP = 34     # Platz fuer Ueberschrift und Monatsnamen

# Fade-Timing: jede Spalte startet minimal spaeter als die vorherige
STAGGER = 0.022    # Sekunden Versatz pro Woche
FADE = 0.45        # Dauer eines einzelnen Fades

THEMES = {
    "light": {
        "empty": "#ebedf0",
        "levels": ["#9be9a8", "#40c463", "#30a14e", "#216e39"],
        "text": "#57606a",
        "stroke": "rgba(27,31,35,0.06)",
    },
    "dark": {
        "empty": "#161b22",
        "levels": ["#0e4429", "#006d32", "#26a641", "#39d353"],
        "text": "#7d8590",
        "stroke": "rgba(240,246,252,0.10)",
    },
}

LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionLevel }
        }
      }
    }
  }
}
"""


def fetch(login, token):
    """Holt den Kalender ueber GitHubs GraphQL-API."""
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
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def month_labels(weeks):
    """Monatsname an der Woche, in der ein neuer Monat beginnt."""
    # erst alle Monatswechsel sammeln
    changes = []
    last_month = None
    for i, week in enumerate(weeks):
        month = int(week["contributionDays"][0]["date"][5:7])
        if month != last_month:
            changes.append((i, month))
            last_month = month

    # dann nur die Monate beschriften, die mindestens 3 Spalten breit sind.
    # Der angeschnittene Monat ganz links faellt dadurch raus, genau wie
    # bei GitHub selbst.
    labels = []
    for k, (i, month) in enumerate(changes):
        end = changes[k + 1][0] if k + 1 < len(changes) else len(weeks)
        if end - i >= 3:
            labels.append((i, MONTHS[month - 1]))
    return labels


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;")


def render(calendar, theme_name):
    t = THEMES[theme_name]
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]

    width = LABEL_LEFT + len(weeks) * PITCH + PAD
    height = LABEL_TOP + 7 * PITCH + 26

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="-apple-system, BlinkMacSystemFont, '
        f'\'Segoe UI\', Helvetica, Arial, sans-serif">',
        "<style>",
        # Zellen starten unsichtbar und faden nacheinander ein
        f".d{{opacity:0;animation:f {FADE}s ease-out forwards}}",
        "@keyframes f{to{opacity:1}}",
        f".t{{fill:{t['text']};font-size:10px}}",
        f".h{{fill:{t['text']};font-size:12px}}",
        "</style>",
        f'<text x="{PAD}" y="16" class="h">{total} contributions in the last year</text>',
    ]

    # Monatsnamen
    for index, name in month_labels(weeks):
        x = LABEL_LEFT + index * PITCH
        out.append(f'<text x="{x}" y="{LABEL_TOP - 6}" class="t">{name}</text>')

    # Wochentage, wie bei GitHub nur Mo/Mi/Fr
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = LABEL_TOP + row * PITCH + CELL - 1
        out.append(f'<text x="{PAD}" y="{y}" class="t">{name}</text>')

    # Das Raster: eine Gruppe pro Woche, damit die Animation nur einmal
    # pro Spalte definiert werden muss
    for w, week in enumerate(weeks):
        x = LABEL_LEFT + w * PITCH
        delay = round(w * STAGGER, 3)
        out.append(f'<g class="d" transform="translate({x},0)" style="animation-delay:{delay}s">')
        for row, day in enumerate(week["contributionDays"]):
            y = LABEL_TOP + row * PITCH
            level = LEVELS[day["contributionLevel"]]
            fill = t["empty"] if level == 0 else t["levels"][level - 1]
            out.append(
                f'<rect y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="{RADIUS}" fill="{fill}" stroke="{t["stroke"]}"/>'
            )
        out.append("</g>")

    # Legende unten rechts
    legend_y = LABEL_TOP + 7 * PITCH + 12
    legend_x = width - PAD - 5 * PITCH - 60
    out.append(f'<text x="{legend_x}" y="{legend_y + 9}" class="t">Less</text>')
    for i, color in enumerate([t["empty"]] + t["levels"]):
        x = legend_x + 30 + i * PITCH
        out.append(
            f'<rect x="{x}" y="{legend_y}" width="{CELL}" height="{CELL}" '
            f'rx="{RADIUS}" fill="{color}" stroke="{t["stroke"]}"/>'
        )
    out.append(
        f'<text x="{legend_x + 30 + 5 * PITCH + 4}" y="{legend_y + 9}" class="t">More</text>'
    )

    out.append("</svg>")
    return "\n".join(out)


def main():
    login = os.environ["GH_LOGIN"]
    token = os.environ["GITHUB_TOKEN"]
    calendar = fetch(login, token)

    os.makedirs("dist", exist_ok=True)
    for theme, filename in (("light", "contributions.svg"),
                            ("dark", "contributions-dark.svg")):
        with open(os.path.join("dist", filename), "w") as f:
            f.write(render(calendar, theme))
        print("wrote", filename)


if __name__ == "__main__":
    main()
