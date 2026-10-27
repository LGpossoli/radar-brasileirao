import os
import re
import secrets
import time
from pathlib import Path

import requests
import streamlit as st

from ui.evaluation import render_evaluation
from ui.presentation import dashboard, display_name, standings

ROOT = Path(__file__).resolve().parents[1]
API = os.environ.get("RADAR_API_URL", "http://127.0.0.1:8000").rstrip("/")
st.set_page_config(page_title="Radar do Brasileirão", page_icon="⚽", layout="wide", menu_items={})
st.set_option("client.toolbarMode", "minimal")
st.markdown(f"<style>{(ROOT / 'ui/style.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


@st.dialog("README — Radar do Brasileirão", width="large", dismissible=False)
def show_readme():
    if st.button("Fechar README"):
        st.rerun()
    content = (ROOT / "README.md").read_text(encoding="utf-8")
    content = re.sub(
        r"\]\(((?:docs|reports)/[^)]+)\)",
        r"](https://github.com/LGpossoli/radar-brasileirao/blob/main/\1)",
        content,
    )
    st.markdown(content)


try:
    response = requests.get(f"{API}/v1/teams", timeout=10)
    response.raise_for_status()
    catalog = response.json()
except (requests.RequestException, ValueError):
    st.error("Serviço indisponível. Tente novamente em instantes.")
    st.stop()


title, model_control, menu = st.columns([12, 4, 0.8], vertical_alignment="center")
with title:
    st.markdown(
        '<div class="brand"><span class="brand-mark">◉</span><h1>Radar do Brasileirão</h1>'
        '<span class="brand-tag">ANÁLISE DE CONFRONTOS</span></div>',
        unsafe_allow_html=True,
    )
with model_control:
    if st.session_state.get("model_id") not in catalog["models"]:
        st.session_state.model_id = catalog["default_model_id"]
    model_id = st.selectbox(
        "Modelo de predição",
        list(catalog["models"]),
        format_func=catalog["models"].get,
        key="model_id",
        label_visibility="collapsed",
        help="Modelo usado no confronto e no campeonato",
    )
with menu:
    with st.popover(
        " ",
        icon=":material/settings:",
        help="Menu do projeto",
        use_container_width=True,
        key=f"project_menu_{st.session_state.get('page', 'analysis')}",
    ):
        if st.button("Avaliação dos modelos", type="tertiary"):
            st.session_state.page = "evaluation"
            st.rerun()
        if st.button("README", type="tertiary"):
            show_readme()
        st.markdown(f"[API · documentação interativa]({API}/docs)")
        st.markdown(f"[API · estado do serviço]({API}/health)")
        st.markdown(f"[API · clubes disponíveis]({API}/v1/teams)")


# Preservo os valores dos seletores quando seus widgets não estão na página de avaliação.
for saved_key in ("home", "away"):
    if saved_key in st.session_state:
        st.session_state[saved_key] = st.session_state[saved_key]
if st.session_state.get("page") == "evaluation":
    render_evaluation(API, model_id)
    st.stop()

labels = {team["id"]: display_name(team["id"], team["name"]) for team in catalog["teams"]}
ids = list(labels)
if not ids:
    st.warning("Nenhum clube disponível.")
    st.stop()
if st.session_state.get("home") not in ids:
    st.session_state.home = "flamengo" if "flamengo" in ids else ids[0]
if st.session_state.get("away") not in ids:
    st.session_state.away = "palmeiras" if "palmeiras" in ids else ids[min(1, len(ids) - 1)]


def swap():
    st.session_state.home, st.session_state.away = st.session_state.away, st.session_state.home


analysis_column, season_column = st.columns([3, 1.1], gap="small")

with analysis_column:
    left, invert, right, action = st.columns([3.5, 1.4, 3.5, 1.5], vertical_alignment="bottom")
    with left:
        st.selectbox("Mandante", ids, format_func=labels.get, key="home")
    with invert:
        st.button("⇄ Inverter", on_click=swap, use_container_width=True, help="Inverter mandante e visitante")
    with right:
        st.selectbox("Visitante", ids, format_func=labels.get, key="away")
    with action:
        refresh = st.button("Analisar", type="primary", use_container_width=True)
    home, away = st.session_state.home, st.session_state.away
    key = (home, away, catalog["data_through"], model_id)
    if home == away:
        st.session_state.pop("analysis", None)
        st.session_state.pop("analysis_key", None)
        st.warning("Escolha dois clubes diferentes.")
    else:
        if refresh or st.session_state.get("analysis_key") != key:
            st.session_state.pop("analysis", None)
            try:
                response = requests.post(
                    f"{API}/v1/predict",
                    json={"home_team_id": home, "away_team_id": away, "model_id": model_id},
                    timeout=20,
                )
                response.raise_for_status()
                st.session_state.analysis = response.json()
                st.session_state.analysis_key = key
            except (requests.RequestException, ValueError):
                st.session_state.pop("analysis_key", None)
                st.error("Não foi possível analisar o confronto. Tente novamente.")
        if result := st.session_state.get("analysis"):
            st.markdown(dashboard(result), unsafe_allow_html=True)
            if result["home"]["limited_history"] or result["away"]["limited_history"]:
                st.caption("Histórico limitado para um dos clubes.")


with season_column:
    st.markdown('<div class="simulation-control-label">Temporada hipotética</div>', unsafe_allow_html=True)
    run_simulation = st.button("Simular temporada", type="primary", use_container_width=True)
    simulation_key = (catalog["data_through"], tuple(ids), model_id)
    if st.session_state.get("simulation_key") != simulation_key:
        st.session_state.pop("simulation", None)
        st.session_state.simulation_key = simulation_key
    placeholder = st.empty()
    empty_rows = [dict(team_id=club, points=0, played=0, wins=0, draws=0, losses=0) for club in ids]
    simulation = st.session_state.get("simulation")
    placeholder.markdown(
        standings(
            simulation["rounds"][-1] if simulation else empty_rows,
            labels,
            len(simulation["rounds"]) if simulation else 0,
            2 * (len(ids) - 1),
            catalog["season"],
        ),
        unsafe_allow_html=True,
    )
    if run_simulation:
        try:
            response = requests.post(
                f"{API}/v1/simulate",
                json={"seed": secrets.randbits(32), "model_id": model_id},
                timeout=30,
            )
            response.raise_for_status()
            simulation = response.json()
            start_time = time.monotonic()
            for index, rows in enumerate(simulation["rounds"], 1):
                time.sleep(max(0, start_time + index - time.monotonic()))
                placeholder.markdown(
                    standings(rows, labels, index, len(simulation["rounds"]), catalog["season"]),
                    unsafe_allow_html=True,
                )
            st.session_state.simulation = simulation
        except (requests.RequestException, ValueError):
            st.error("Não consegui simular o campeonato. Tente novamente.")


year, month, day = catalog["data_through"].split("-")
st.markdown(
    f'<div class="bottom-line"><span>SÉRIE A · {catalog["season"]}</span>'
    f"<span>Dados até {day}/{month}/{year}</span><span>Adão Duque · Kaggle</span></div>",
    unsafe_allow_html=True,
)
