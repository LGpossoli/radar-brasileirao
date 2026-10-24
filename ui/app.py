import os

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

API = os.environ.get("RADAR_API_URL", "http://127.0.0.1:8000").rstrip("/")
st.set_page_config(page_title="Radar do Brasileirão", page_icon="⚽", layout="wide")
st.markdown(
    """<style>
.block-container {max-width:1180px;padding-top:2.6rem;}
h1 {font-family:Georgia,serif!important;font-size:3.6rem!important;letter-spacing:-2px;}
h2,h3 {letter-spacing:-.5px;}
.eyebrow {color:#d6ee52;letter-spacing:3px;font-size:.75rem;font-weight:700;}
.intro {max-width:680px;font-size:1.08rem;color:#b1c8bf;margin-bottom:1.5rem;}
[data-testid="stMetric"] {border-top:3px solid #d6ee52;padding:18px;background:#142622;border-radius:2px;}
[data-testid="stMetricValue"] {font-size:2.8rem;font-weight:800;}
button[kind="primary"], button[kind="primary"] p {color:#10231c;font-weight:800;min-height:48px;}
footer {visibility:hidden;}
</style>""",
    unsafe_allow_html=True,
)
st.markdown('<div class="eyebrow">FUTEBOL BRASILEIRO / ANÁLISE DE DADOS</div>', unsafe_allow_html=True)
st.title("O jogo começa nos dados.")
st.markdown(
    '<div class="intro">Compare o momento de dois clubes e explore as probabilidades '
    "de um confronto. Você escolhe o mando. O histórico entra em campo.</div>",
    unsafe_allow_html=True,
)


def get_teams():
    response = requests.get(f"{API}/v1/teams", timeout=10)
    response.raise_for_status()
    return response.json()


try:
    catalog = get_teams()
except (requests.RequestException, ValueError):
    st.error("A API está indisponível. Inicie o serviço e recarregue esta página.")
    st.caption("Consulte as instruções de execução no README do projeto.")
    st.stop()

date_label = pd.Timestamp(catalog["data_through"]).strftime("%d/%m/%Y")
st.info(
    f"Base histórica até {date_label} · Série A {catalog['season']}. "
    "As estimativas não incorporam acontecimentos posteriores a essa data."
)
labels = {team["id"]: team["name"] for team in catalog["teams"]}
ids = list(labels)
with st.container(border=True):
    st.subheader("Monte o confronto")
    with st.form("confronto"):
        left, right = st.columns(2)
        home = left.selectbox(
            "Mandante · joga em casa",
            ids,
            format_func=labels.get,
            index=ids.index("flamengo") if "flamengo" in ids else 0,
        )
        away = right.selectbox(
            "Visitante · joga fora",
            ids,
            format_func=labels.get,
            index=ids.index("palmeiras") if "palmeiras" in ids else min(1, len(ids) - 1),
        )
        submitted = st.form_submit_button("Analisar confronto →", type="primary", use_container_width=True)

if submitted:
    st.session_state.pop("analysis", None)
    if home == away:
        st.warning("Escolha dois clubes diferentes para analisar o confronto.")
    else:
        try:
            with st.spinner("Calculando probabilidades e comparando históricos..."):
                response = requests.post(
                    f"{API}/v1/predict", json={"home_team_id": home, "away_team_id": away}, timeout=20
                )
                response.raise_for_status()
                st.session_state.analysis = response.json()
        except (requests.RequestException, ValueError):
            st.error(
                "Não foi possível analisar este confronto. Confira se a API está disponível e tente novamente."
            )

result = st.session_state.get("analysis")
if result:
    st.caption(f"RESULTADO DA ANÁLISE · {result['home']['name']} × {result['away']['name']}")
    a, b, c = st.columns(3)
    a.metric(f"Vitória · {result['home']['name']}", f"{result['probabilities']['home_win']:.1%}")
    b.metric("Empate", f"{result['probabilities']['draw']:.1%}")
    c.metric(f"Vitória · {result['away']['name']}", f"{result['probabilities']['away_win']:.1%}")
    st.caption("Os percentuais exatos somam 100%; arredondamentos de exibição podem diferir em 0,1 ponto.")
    comparisons, meetings, methodology = st.tabs(
        ["Momento dos clubes", "Confrontos diretos", "Como ler a análise"]
    )
    with comparisons:
        rows = []
        for field, label in [
            ("points_percentage_5", "Aproveitamento · últimos 5 (%)"),
            ("points_percentage_10", "Aproveitamento · últimos 10 (%)"),
            ("goals_scored_5", "Gols marcados por jogo · últimos 5"),
            ("goals_conceded_5", "Gols sofridos por jogo · últimos 5"),
            ("venue_points_percentage_10", "Aproveitamento no mando · últimos 10 (%)"),
            ("venue_goals_scored_10", "Gols marcados no mando · últimos 10"),
            ("venue_goals_conceded_10", "Gols sofridos no mando · últimos 10"),
        ]:
            rows.append(
                {
                    "Indicador": label,
                    result["home"]["name"]: result["home"][field],
                    result["away"]["name"]: result["away"][field],
                }
            )
        st.dataframe(pd.DataFrame(rows).set_index("Indicador").round(2), use_container_width=True)
        for side in ["home", "away"]:
            team = result[side]
            st.write(f"**{team['name']}** · {'  '.join(team['recent_form'])}")
        st.caption(
            "V = vitória · E = empate · D = derrota. Ordem: do mais antigo ao mais recente. "
            "No mando: jogos em casa para o mandante e fora para o visitante."
        )
        fig = go.Figure()
        for side, color in [("home", "#d6ee52"), ("away", "#69c7b2")]:
            team = result[side]
            fig.add_bar(
                name=team["name"],
                x=["Últimos 5", "Últimos 10", "No mando"],
                y=[
                    team["points_percentage_5"],
                    team["points_percentage_10"],
                    team["venue_points_percentage_10"],
                ],
                marker_color=color,
            )
        fig.update_layout(
            title="Aproveitamento de pontos",
            yaxis_range=[0, 100],
            yaxis_title="% dos pontos",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#edf3ea",
            height=330,
            margin=dict(t=45, b=10),
            barmode="group",
        )
        st.plotly_chart(fig, use_container_width=True)
    with meetings:
        if not result["head_to_head"]:
            st.info("Não há confrontos diretos na base disponível.")
        for match in result["head_to_head"]:
            st.write(
                f"{pd.Timestamp(match['date']).strftime('%d/%m/%Y')} · **{match['home']} "
                f"{match['home_goals']} × {match['away_goals']} {match['away']}**"
            )
    with methodology:
        st.write(
            "O modelo compara forma recente, gols, mando de campo e força relativa (Elo). "
            "Os indicadores descrevem o histórico; não são explicações causais da previsão."
        )
        st.write(
            "A avaliação usa temporadas posteriores às de treinamento. A previsão não inclui "
            "lesões, escalações, transferências ou jogos de outras competições."
        )
        st.caption(f"Modelo {result['model_version']} · Treinado até {result['trained_through']}")
    for warning in result["warnings"]:
        st.caption(warning)
else:
    st.markdown("---")
    st.subheader("Três resultados. Uma leitura mais informada.")
    st.write(
        "Explore o peso do mando, compare o aproveitamento e confira o histórico de encontros. "
        "Escolha os clubes acima para começar."
    )

st.markdown("---")
st.caption(
    "RADAR DO BRASILEIRÃO · Dados: Adão Duque / Kaggle · Probabilidades são estimativas, não garantias."
)
st.link_button(
    "Conheça a base de dados", "https://www.kaggle.com/datasets/adaoduque/campeonato-brasileiro-de-futebol"
)
