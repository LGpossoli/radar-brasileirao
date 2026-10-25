"""Apresentação em português, paletas dos clubes e gráfico vetorial acessível."""

import math
from html import escape

PALETTES = {
    "atletico-mg": ["#181818", "#ffffff"],
    "bahia": ["#1468c6", "#df2638", "#ffffff"],
    "botafogo-rj": ["#181818", "#ffffff"],
    "bragantino": ["#ffffff", "#dc2030", "#181818"],
    "ceara": ["#181818", "#ffffff"],
    "corinthians": ["#ffffff", "#181818"],
    "cruzeiro": ["#1769ce", "#ffffff"],
    "flamengo": ["#dc2338", "#181818"],
    "fluminense": ["#8d243c", "#16794b", "#ffffff"],
    "fortaleza": ["#245bc0", "#df2638", "#ffffff"],
    "gremio": ["#28a5df", "#181818", "#ffffff"],
    "internacional": ["#dc2338", "#ffffff"],
    "juventude": ["#169552", "#ffffff"],
    "mirassol": ["#f3d629", "#13763c"],
    "palmeiras": ["#178349", "#ffffff"],
    "santos": ["#ffffff", "#181818"],
    "sao-paulo": ["#df2638", "#ffffff", "#181818"],
    "sport": ["#dc2338", "#181818", "#e9ba37"],
    "vasco": ["#181818", "#ffffff", "#dc2338"],
    "vitoria": ["#dc2338", "#181818"],
}
NAMES = {
    "atletico-mg": "Atlético-MG",
    "botafogo-rj": "Botafogo",
    "ceara": "Ceará",
    "gremio": "Grêmio",
    "sao-paulo": "São Paulo",
    "vitoria": "Vitória",
}


def display_name(club, fallback):
    return NAMES.get(club, fallback)


def rgb(color):
    return tuple(int(color[i : i + 2], 16) / 255 for i in (1, 3, 5))


def luminance(color):
    channels = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb(color)]
    return sum(v * w for v, w in zip(channels, (0.2126, 0.7152, 0.0722)))


def text_color(background):
    level = luminance(background)
    return "#000000" if (level + 0.05) / 0.05 >= 1.05 / (level + 0.05) else "#ffffff"


def team_colors(home, away):
    first = PALETTES.get(home, ["#d6ee52", "#ffffff"])
    second = PALETTES.get(away, ["#69c7b2", "#181818"])

    def distance(a, b):
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(rgb(a), rgb(b))))

    if distance(first[0], second[0]) >= 0.52:
        return first[0], second[0]
    return max(((a, b) for a in first for b in second), key=lambda pair: distance(*pair))


def number(value, digits=1, suffix=""):
    return "—" if value is None else f"{value:.{digits}f}".replace(".", ",") + suffix


def donut(probabilities, labels, colors):
    parts = []
    angle = -90
    for probability, label, color in zip(probabilities, labels, colors):
        sweep = probability * 360
        if sweep <= 0:
            continue
        start = math.radians(angle)
        middle = math.radians(angle + sweep / 2)
        end = math.radians(angle + sweep)
        x1, y1 = 130 + 112 * math.cos(start), 130 + 112 * math.sin(start)
        xm, ym = 130 + 112 * math.cos(middle), 130 + 112 * math.sin(middle)
        x2, y2 = 130 + 112 * math.cos(end), 130 + 112 * math.sin(end)
        parts.append(
            f'<path d="M130 130 L{x1:.3f} {y1:.3f} A112 112 0 0 1 {xm:.3f} {ym:.3f} '
            f'A112 112 0 0 1 {x2:.3f} {y2:.3f} Z" fill="{color}" stroke="none">'
            f"<title>{escape(label)}: {number(probability * 100)}%</title></path>"
        )
        if probability >= 0.06:
            mid = math.radians(angle + sweep / 2)
            parts.append(
                f'<text x="{130 + 88 * math.cos(mid):.2f}" y="{130 + 88 * math.sin(mid):.2f}" '
                f'fill="{text_color(color)}" text-anchor="middle" dominant-baseline="middle" '
                f'font-size="14" font-weight="800">{number(probability * 100)}%</text>'
            )
        angle += sweep
    return (
        '<svg class="prob-chart" viewBox="0 0 260 260" role="img" '
        'aria-label="Probabilidades de vitória do mandante, empate e vitória do visitante">'
        + "".join(parts)
        + '<circle cx="130" cy="130" r="60" fill="#14231f"/>'
        '<text x="130" y="126" text-anchor="middle" fill="#f4f6ef" font-size="20" font-weight="700">'
        'Confronto</text><text x="130" y="149" text-anchor="middle" fill="#b9c9c1" font-size="12">'
        "PROBABILIDADES</text></svg>"
    )


def dashboard(result):
    home, away = result["home"], result["away"]
    hn, an = display_name(home["team_id"], home["name"]), display_name(away["team_id"], away["name"])
    hc, ac = team_colors(home["team_id"], away["team_id"])
    labels = [f"Vitória do {hn}", "Empate", f"Vitória do {an}"]
    probs = [result["probabilities"][key] for key in ("home_win", "draw", "away_win")]
    colors = [hc, "#89979f", ac]
    legend = "".join(
        f'<div class="legend-row"><span class="swatch" style="background:{c}"></span>'
        f"<span>{escape(label)}</span><strong>{number(p * 100)}%</strong></div>"
        for label, p, c in zip(labels, probs, colors)
    )
    metrics = [
        ("points_percentage_5", "Aproveitamento · 5 jogos", "%"),
        ("points_percentage_10", "Aproveitamento · 10 jogos", "%"),
        ("goals_scored_5", "Gols marcados · 5 jogos", ""),
        ("goals_conceded_5", "Gols sofridos · 5 jogos", ""),
        ("venue_points_percentage_10", "Aproveitamento no mando¹", "%"),
        ("venue_goals_scored_10", "Gols marcados no mando¹", ""),
        ("venue_goals_conceded_10", "Gols sofridos no mando¹", ""),
    ]
    rows = "".join(
        f"<tr><th>{label}</th><td>{number(home[field], suffix=suffix)}</td>"
        f"<td>{number(away[field], suffix=suffix)}</td></tr>"
        for field, label, suffix in metrics
    )
    forms = []
    for team, name in [(home, hn), (away, an)]:
        badges = "".join(
            f'<span class="form-badge form-{v}" title="{dict(V="Vitória", E="Empate", D="Derrota")[v]}">{v}</span>'
            for v in team["recent_form"]
        )
        forms.append(f'<div class="form-row"><span>{escape(name)}</span><div>{badges}</div></div>')
    meetings = []
    for game in result["head_to_head"]:
        year, month, day = game["date"].split("-")
        # Uso os nomes do catálogo com os acentos exibidos na tela.
        from radar.data import team_id

        h = display_name(team_id(game["home"]), game["home"])
        a = display_name(team_id(game["away"]), game["away"])
        meetings.append(
            f'<div class="meeting"><time>{day}/{month}/{year}</time><div class="score-row">'
            f"<span>{escape(h)}</span><b>{game['home_goals']} × {game['away_goals']}</b>"
            f"<span>{escape(a)}</span></div></div>"
        )
    return (
        f'<div class="dashboard"><section class="panel probability"><h2>Probabilidades</h2>'
        f'{donut(probs, labels, colors)}<div class="legend">{legend}</div></section>'
        f'<section class="panel comparison"><h2>Desempenho recente</h2><table class="stats">'
        f'<thead><tr><th>Indicador</th><th><i style="background:{hc}"></i>{escape(hn)}</th>'
        f'<th><i style="background:{ac}"></i>{escape(an)}</th></tr></thead><tbody>{rows}</tbody></table>'
        f'<div class="forms">{"".join(forms)}</div><div class="micro">¹ Últimos 10 no mando · Gols por jogo</div>'
        f'</section><section class="panel meetings"><h2>Confrontos diretos</h2>'
        f"{''.join(meetings) or '<p>Nenhum confronto disponível.</p>'}</section></div>"
    )


def standings(rows, labels, round_number, total_rounds=38):
    body = "".join(
        f"<tr><td>{position}</td><th>{escape(labels[row['team_id']])}</th>"
        + "".join(f"<td>{row[field]}</td>" for field in ("points", "played", "wins", "draws", "losses"))
        + "</tr>"
        for position, row in enumerate(rows, 1)
    )
    return (
        f'<div class="league-caption">Rodada {round_number} de {total_rounds} · Cenário hipotético</div>'
        '<div class="league-table"><table><thead><tr><th>#</th><th>Clube</th>'
        "<th>P</th><th>J</th><th>V</th><th>E</th><th>D</th></tr></thead>"
        f"<tbody>{body}</tbody></table></div>"
    )
