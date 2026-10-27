"""Mostro o teste histórico separadamente da análise hipotética."""

from html import escape

import pandas as pd
import requests
import streamlit as st

from ui.presentation import number

MODEL_NAMES = {
    "regressao_logistica": "Regressão Logística",
    "arvore_decisao": "Árvore de Decisão",
    "random_forest": "Random Forest",
    "frequencias": "Frequências históricas",
}
RESULT_NAMES = {"H": "Vitória do mandante", "D": "Empate", "A": "Vitória do visitante"}


def filtered_matches(matches, season, club, outcome):
    return [
        row
        for row in matches
        if (season == "Todas" or row["season"] == season)
        and (club == "Todos" or club in (row["home"], row["away"]))
        and (outcome == "Todos" or row["correct"] == (outcome == "Acertos"))
    ]


def render_evaluation(api, model_id):
    if st.button("← Voltar à análise"):
        st.session_state.page = "analysis"
        st.rerun()
    st.markdown("## Avaliação dos modelos")
    try:
        response = requests.get(f"{api}/v1/evaluation", params={"model_id": model_id}, timeout=20)
        response.raise_for_status()
        report = response.json()
    except (requests.RequestException, ValueError):
        st.warning(
            "Avaliação indisponível. A análise de confrontos continua disponível. "
            "Para gerar o relatório, execute python -m radar.train."
        )
        return
    stages = [
        ("Treinamento", "train", "Aprender padrões"),
        ("Validação", "validation", "Comparar e escolher o padrão"),
        ("Teste histórico", "test", "Medir em partidas fora do ajuste"),
        ("Modelo disponível na análise", "production", "Retreinamento para uso"),
    ]
    for column, (title, key, description) in zip(st.columns(4), stages):
        with column:
            st.markdown(
                f'<div class="stage"><strong>{title}</strong><b>{escape(report["periods"][key])}</b>'
                f"<span>{description}</span></div>",
                unsafe_allow_html=True,
            )
    st.caption(
        "Divisão por temporada: 2020 inclui partidas de 2021. Avaliação histórica retrospectiva; "
        "os resultados do teste já foram consultados em versões anteriores."
    )
    st.markdown(f"### {report['model_name']} · teste completo de 2023–2024")
    metrics = report["metrics"]
    for col, title, value in zip(
        st.columns(4),
        ["Partidas avaliadas", "Acertos", "Erros", "Taxa de acerto"],
        [metrics["total"], metrics["hits"], metrics["errors"], number(metrics["accuracy"] * 100, suffix="%")],
    ):
        col.metric(title, value)
    st.caption(
        f"F1 macro: {number(metrics['f1_macro'], 3)} · equilíbrio entre as três classes (maior é melhor). "
        f"Log loss: {number(metrics['log_loss'], 4)} · qualidade das probabilidades (menor é melhor)."
    )
    comparison = pd.DataFrame(
        [
            {
                "Modelo": MODEL_NAMES[key],
                "Acertos": value["hits"],
                "Erros": value["errors"],
                "Taxa de acerto": number(value["accuracy"] * 100, suffix="%"),
                "F1 macro": number(value["f1_macro"], 3),
                "Log loss": number(value["log_loss"], 4),
            }
            for key, value in report["comparison"].items()
        ]
    )
    st.markdown(
        '<div class="evaluation-comparison">' + comparison.to_html(index=False, escape=True) + "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Acerto significa acertar vitória, empate ou derrota, não o placar exato. "
        "Uma probabilidade não é uma promessa de resultado. O padrão foi escolhido na validação, não nesta tabela de teste."
    )
    games = report["matches"]
    clubs = sorted({name for row in games for name in (row["home"], row["away"])})
    c1, c2, c3 = st.columns(3)
    season = c1.selectbox("Temporada do teste", ["Todas", 2023, 2024], key="eval_season")
    club = c2.selectbox("Clube", ["Todos", *clubs], key="eval_club")
    outcome = c3.selectbox("Resultado da previsão", ["Todos", "Acertos", "Erros"], key="eval_outcome")
    selected = filtered_matches(games, season, club, outcome)
    st.caption(
        f"{len(selected)} de {len(games)} partidas após os filtros. Os indicadores acima permanecem referentes ao teste completo."
    )
    table = []
    for row in sorted(selected, key=lambda item: (item["date"], item["id"]), reverse=True):
        year, month, day = row["date"].split("-")
        table.append(
            {
                "Data": f"{day}/{month}/{year}",
                "Confronto": f"{row['home']} × {row['away']}",
                "Mandante": number(row["probabilities"]["H"] * 100, suffix="%"),
                "Empate": number(row["probabilities"]["D"] * 100, suffix="%"),
                "Visitante": number(row["probabilities"]["A"] * 100, suffix="%"),
                "Mais provável": RESULT_NAMES[row["predicted"]],
                "Placar real": f"{row['home_goals']} × {row['away_goals']}",
                "Resultado real": RESULT_NAMES[row["actual"]],
                "Avaliação": "Acertou" if row["correct"] else "Errou",
            }
        )
    if table:
        st.markdown(
            '<div class="evaluation-games">'
            + pd.DataFrame(table).to_html(index=False, escape=True)
            + "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("Nenhuma partida corresponde aos filtros.")
