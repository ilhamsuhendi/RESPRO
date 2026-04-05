"""
main.py — RESPRO (Reservoir Profile) Application Entry Point

Central router for the multipage Streamlit app. Defines navigation
across the Home landing page and the three production viewers.
Run with: streamlit run main.py
"""

import streamlit as st

# ── Page Configuration (must be first Streamlit command) ─────
st.set_page_config(
    page_title="RESPRO — Reservoir Profile",
    page_icon="🛢️",
    layout="wide"
)

# ── Page Definitions ─────────────────────────────────────────
home_page = st.Page("views/home.py", title="Home", icon="🏠", default=True)
fc_page = st.Page("views/fc_viewer.py", title="FC Viewer", icon="📊")
ltp_page = st.Page("views/ltp_viewer.py", title="LTP Viewer", icon="📈")
prosum_page = st.Page("views/pro_sum.py", title="ProSum", icon="📋")

# ── Navigation ───────────────────────────────────────────────
pg = st.navigation({
    "": [home_page],
    "Viewers": [fc_page, ltp_page, prosum_page],
})

pg.run()
