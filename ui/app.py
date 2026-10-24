import os
import re
from pathlib import Path

import requests
import streamlit as st

from ui.presentation import dashboard, display_name

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


title, menu = st.columns([20, 1], vertical_alignment="center")
with title:
    st.markdown(
        '<div class="brand"><span class="brand-mark">◉</span><h1>Radar do Brasileirão</h1>'
        '<span class="brand-tag">ANÁLISE DE CONFRONTOS</span></div>',
        unsafe_allow_html=True,
    )
with menu:
    with st.popover("⋮", help="Menu do projeto", use_container_width=True):
        if st.button("Ler README", use_container_width=True):
            show_readme()
        st.download_button(
            "Baixar README",
            (ROOT / "README.md").read_text(encoding="utf-8"),
            file_name="README.md",
            mime="text/markdown",
            use_container_width=True,
        )

try:
    response = requests.get(f"{API}/v1/teams", timeout=10)
    response.raise_for_status()
    catalog = response.json()
except (requests.RequestException, ValueError):
    st.error("Serviço indisponível. Tente novamente em instantes.")
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


left, invert, right, action = st.columns([5, 1.45, 5, 2.3], vertical_alignment="bottom")
with left:
    st.selectbox("Mandante", ids, format_func=labels.get, key="home")
with invert:
    st.button("⇄ Inverter", on_click=swap, use_container_width=True, help="Inverter mandante e visitante")
with right:
    st.selectbox("Visitante", ids, format_func=labels.get, key="away")
with action:
    refresh = st.button("Analisar", type="primary", use_container_width=True)

home, away = st.session_state.home, st.session_state.away
key = (home, away, catalog["data_through"])
if home == away:
    st.session_state.pop("analysis", None)
    st.session_state.pop("analysis_key", None)
    st.warning("Escolha dois clubes diferentes.")
else:
    if refresh or st.session_state.get("analysis_key") != key:
        st.session_state.pop("analysis", None)
        try:
            response = requests.post(
                f"{API}/v1/predict", json={"home_team_id": home, "away_team_id": away}, timeout=20
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

year, month, day = catalog["data_through"].split("-")
st.markdown(
    f'<div class="bottom-line"><span>SÉRIE A · {catalog["season"]}</span>'
    f"<span>Dados até {day}/{month}/{year}</span><span>Adão Duque · Kaggle</span></div>",
    unsafe_allow_html=True,
)
