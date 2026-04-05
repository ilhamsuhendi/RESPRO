"""
Home — RESPRO Landing Page

Visual dashboard with navigation cards for the three production viewers.
Each card provides a title, description, and st.switch_page button.
"""

import streamlit as st

# ── Custom CSS for the Landing Page ──────────────────────────
st.markdown("""
<style>
    /* Hero section styling */
    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        color: #117EA8;
        text-align: center;
        margin-bottom: 0.2rem;
        font-family: 'Inter', 'Outfit', sans-serif;
    }
    .hero-subtitle {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        margin-bottom: 2.5rem;
        font-weight: 400;
    }

    /* Navigation card styling */
    .nav-card {
        background: linear-gradient(135deg, #f8fbfd 0%, #eef6fa 100%);
        border: 1px solid #d4e8f0;
        border-radius: 16px;
        padding: 2rem 1.5rem;
        text-align: center;
        min-height: 280px;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(17, 126, 168, 0.06);
    }
    .nav-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(17, 126, 168, 0.15);
        border-color: #117EA8;
    }
    .nav-card .card-icon {
        font-size: 3rem;
        margin-bottom: 0.8rem;
    }
    .nav-card .card-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #1a3a4a;
        margin-bottom: 0.6rem;
    }
    .nav-card .card-desc {
        font-size: 0.95rem;
        color: #666;
        line-height: 1.5;
        margin-bottom: 1.2rem;
    }

    /* Divider line */
    .hero-divider {
        width: 80px;
        height: 4px;
        background: linear-gradient(90deg, #117EA8, #99DAF4);
        margin: 0 auto 2rem auto;
        border-radius: 2px;
    }
</style>
""", unsafe_allow_html=True)

# ── Hero Section ─────────────────────────────────────────────
st.markdown('<div class="hero-title">🛢️ RESPRO</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Reservoir Profile — Production Intelligence Suite</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-divider"></div>', unsafe_allow_html=True)

# ── Navigation Cards ─────────────────────────────────────────
col1, col2, col3 = st.columns(3, gap="large")

with col1:
    with st.container():
        st.markdown("""
        <div class="nav-card">
            <div class="card-icon">📊</div>
            <div class="card-title">FC Viewer</div>
            <div class="card-desc">
                Monthly gas &amp; condensate production profiles with stacked bar charts
                and comparison line overlays across forecast cases (BDG, FC1, FC2, FC3).
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Open FC Viewer →", key="btn_fc", use_container_width=True):
            st.switch_page("views/fc_viewer.py")

with col2:
    with st.container():
        st.markdown("""
        <div class="nav-card">
            <div class="card-icon">📈</div>
            <div class="card-title">LTP Viewer</div>
            <div class="card-desc">
                Long-term plan stacked area profiles with multi-case overlays,
                production data tables, and field-level assumption comparison.
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Open LTP Viewer →", key="btn_ltp", use_container_width=True):
            st.switch_page("views/ltp_viewer.py")

with col3:
    with st.container():
        st.markdown("""
        <div class="nav-card">
            <div class="card-icon">📋</div>
            <div class="card-title">ProSum</div>
            <div class="card-desc">
                Executive production summary with EUR &amp; Recovery Factor calculations,
                yearly rate charts, and per-field detail tables.
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Open ProSum →", key="btn_prosum", use_container_width=True):
            st.switch_page("views/pro_sum.py")

# ── Footer ───────────────────────────────────────────────────
st.markdown("---")
st.caption("RESPRO v1.0 — Reservoir Profile Intelligence Suite")
