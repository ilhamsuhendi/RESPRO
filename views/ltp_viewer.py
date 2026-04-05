"""
ltp_viewer.py — Long-Term Plan (LTP) Production Viewer

Displays monthly gas and condensate production profiles as stacked area charts
with optional line overlays for case comparison. Includes tabular data views
and assumption comparison across fields and cases.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# ── Constants ────────────────────────────────────────────────
# Canonical field stacking order — controls visual layering in charts.
FIELD_ORDER = ["JKK", "MKS", "MKSE", "MAHA", "GLO", "GDG", "BKA", "WSN"]
AVAILABLE_CASES = ["SP25_28", "SP26_30"]

# Position-based palettes: each field index maps to a fixed color
# so visual identity stays consistent regardless of filter selection.
AREA_COLORS = [
    "#FF0000", "#DEB200", "#FFEB99", "#A6A6A6",
    "#BFBFBF", "#D9D9D9", "#e377c2", "#7f7f7f"
]
LINE_COLORS = [
    "#B30000", "#E79054", "#FFC412", "#818181",
    "#B1B1B1", "#ECECEC", "#000000", "#333333"
]


# ── Styling ──────────────────────────────────────────────────
def inject_custom_css():
    """Applies premium styling: tab typography, background, sidebar refinement."""
    st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stCheckbox {
        font-weight: 500;
        color: #1a1a1a;
    }
    .sidebar .sidebar-content {
        background-image: linear-gradient(#2e3b4e, #2e3b4e);
        color: white;
    }
    h1 {
        color: #2c3e50;
        font-family: 'Outfit', 'Inter', sans-serif;
    }
    /* Font for tabs 40% larger */
    button[data-baseweb="tab"] p {
        font-size: 1.4rem !important;
        font-weight: 600;
    }
    /* Ensuring fonts under the profile tab (and others) are consistently larger */
    .stTabs [data-testid="stMarkdownContainer"] p {
        font-size: 1.1rem; /* Slightly larger base font */
    }
    /* Set selected tab label color to #117EA8 */
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] p {
        color: #117EA8 !important;
    }
    /* Branded checkbox tick color */
    div[data-testid="stCheckbox"] div[role="checkbox"][aria-checked="true"] {
        background-color: #117EA8 !important;
        border-color: #117EA8 !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ── Data Loading ─────────────────────────────────────────────
@st.cache_data
def load_all_data(file_path):
    """
    Loads Profile and Assumption sheets from the LTP database.

    Args:
        file_path: Path to the LTP Excel file.
    Returns:
        tuple: (df_profile, df_assumption) DataFrames.
    """
    df_profile = pd.read_excel(file_path, sheet_name='Profile')
    df_profile['Date'] = pd.to_datetime(df_profile['Date'], errors='coerce')
    df_profile = df_profile.dropna(subset=['Date'])

    df_assumption = pd.read_excel(file_path, sheet_name='Assumption')
    return df_profile, df_assumption


# ── Helpers ──────────────────────────────────────────────────
def normalize_field_name(raw_name):
    """
    Maps a raw field name to its canonical FIELD_ORDER form via
    case-insensitive matching (e.g., 'jkk' → 'JKK').
    """
    return next((f for f in FIELD_ORDER if f.lower() == raw_name.lower()), raw_name)


def build_cumulative_pivot(df, case_name, column_name, fields, dates):
    """
    Pivots a single case's data and returns cumulative sums across fields,
    which is required for stacked area rendering.

    Returns:
        DataFrame or None: Cumulative sum pivot, or None if case is empty.
    """
    case_df = df[df['Case'] == case_name]
    if case_df.empty:
        return None

    pivot = case_df.pivot(
        index='Date', columns='Field', values=column_name
    ).reindex(index=dates).fillna(0)

    # Stack fields in canonical order for visual consistency
    current_order = [f for f in FIELD_ORDER if f in fields and f in pivot.columns]
    pivot = pivot[current_order]
    return pivot.cumsum(axis=1)


def determine_chart_mode(selected_cases):
    """
    Determines which case renders as filled area (primary) vs. line overlay.
    SP26_30 always takes priority as the area case when both are selected,
    since it represents the newer plan.

    Returns:
        tuple: (area_case, line_case) — either may be None.
    """
    area_case, line_case = None, None

    if len(selected_cases) == 1:
        area_case = selected_cases[0]
    elif "SP26_30" in selected_cases and "SP25_28" in selected_cases:
        area_case = "SP26_30"
        line_case = "SP25_28"
    else:
        area_case = selected_cases[0]
        if len(selected_cases) > 1:
            line_case = selected_cases[1]

    return area_case, line_case


# ── Sidebar ──────────────────────────────────────────────────
def render_sidebar(df_profile):
    """
    Renders sidebar filter controls for Field and Case selection.
    Field checkboxes follow canonical FIELD_ORDER.

    Returns:
        tuple: (selected_fields, actual_fields_to_filter, selected_cases)
    """
    # Field Selection — case-insensitive matching against database values
    st.sidebar.subheader("Fields")
    db_fields_lower = [f.lower() for f in df_profile['Field'].unique()]
    db_field_map = {f.lower(): f for f in df_profile['Field'].unique()}

    selected_fields = []
    for field in FIELD_ORDER:
        if field.lower() in db_fields_lower:
            if st.sidebar.checkbox(field, value=True, key=f"field_{field}"):
                selected_fields.append(field)

    # Map canonical names back to database-native names for filtering
    actual_fields_to_filter = [db_field_map[f.lower()] for f in selected_fields]

    # Case Selection
    st.sidebar.subheader("Cases")
    selected_cases = []
    for case in AVAILABLE_CASES:
        if st.sidebar.checkbox(case, value=True, key=f"case_{case}"):
            selected_cases.append(case)

    return selected_fields, actual_fields_to_filter, selected_cases


# ── Visualization ────────────────────────────────────────────
def plot_stacked_profile(df, column_name, title, y_axis_label,
                         selected_fields, selected_cases):
    """
    Creates a stacked area + optional line overlay chart for production rates.

    The 'area' case is rendered as filled stacked areas showing each field's
    contribution. The 'line' case (if present) is overlaid as solid stacked
    lines for visual comparison.

    Returns:
        go.Figure: The assembled Plotly figure.
    """
    fig = go.Figure()
    unique_dates = sorted(df['Date'].unique())
    area_case, line_case = determine_chart_mode(selected_cases)

    # Area traces (primary case)
    if area_case:
        cum_df_area = build_cumulative_pivot(
            df, area_case, column_name, selected_fields, unique_dates
        )
        if cum_df_area is not None:
            for i, field in enumerate(cum_df_area.columns):
                color_idx = min(i, len(AREA_COLORS) - 1)
                fig.add_trace(go.Scatter(
                    x=unique_dates, y=cum_df_area[field].values, mode='lines',
                    name=f"{field} ({area_case} - Area)",
                    line=dict(width=0.5, color=AREA_COLORS[color_idx]),
                    fill='tonexty' if i > 0 else 'tozeroy',
                    fillcolor=AREA_COLORS[color_idx],
                    legendgroup=area_case,
                    legendgrouptitle_text=f"Case {area_case} (Area)"
                ))

    # Line traces (secondary/comparison case)
    if line_case:
        cum_df_line = build_cumulative_pivot(
            df, line_case, column_name, selected_fields, unique_dates
        )
        if cum_df_line is not None:
            for i, field in enumerate(cum_df_line.columns):
                color_idx = min(i, len(LINE_COLORS) - 1)
                fig.add_trace(go.Scatter(
                    x=unique_dates, y=cum_df_line[field].values, mode='lines',
                    name=f"{field} ({line_case} - Line)",
                    line=dict(width=2.5, color=LINE_COLORS[color_idx], dash='solid'),
                    legendgroup=line_case,
                    legendgrouptitle_text=f"Case {line_case} (Line)"
                ))

    # Layout styling — preserving all original parameters
    fig.update_layout(
        title=dict(text=title, font=dict(size=24)),
        xaxis_title="",
        yaxis_title=y_axis_label,
        xaxis=dict(
            showline=True, linewidth=2, linecolor='black',
            showgrid=False, tickmode='linear', dtick="M12",
            tickformat="%Y", ticks="outside", ticklen=5, tickwidth=2,
            title_font=dict(size=18), tickfont=dict(size=14)
        ),
        yaxis=dict(
            showgrid=True, gridcolor='lightgrey',
            title_font=dict(size=18), tickfont=dict(size=14),
            rangemode='tozero'
        ),
        legend=dict(font=dict(size=14), groupclick="toggleitem"),
        font=dict(size=16),
        hovermode="x unified",
        template="plotly_white",
        height=600
    )
    return fig


# ── Tab Renderers ────────────────────────────────────────────
def render_profile_tab(profile_filtered, selected_fields, selected_cases):
    """Renders the Profile tab with Gas and Condensate sub-tabs."""
    sub_tab_gas, sub_tab_cond = st.tabs(["Gas", "Condensate"])

    with sub_tab_gas:
        fig_gas = plot_stacked_profile(
            profile_filtered, "Gas Rate",
            "Monthly Gas Production Rate Stacked Profile",
            "Gas, MMscfd", selected_fields, selected_cases
        )
        st.plotly_chart(fig_gas, use_container_width=True)

    with sub_tab_cond:
        fig_cond = plot_stacked_profile(
            profile_filtered, "Condensate Rate",
            "Monthly Condensate Production Rate Stacked Profile",
            "Condensate, bbld", selected_fields, selected_cases
        )
        st.plotly_chart(fig_cond, use_container_width=True)


def render_table_tab(profile_filtered):
    """Renders per-field/case sub-tabs showing production data tables."""
    st.subheader("Production Data")

    pairs = (profile_filtered[['Field', 'Case']]
             .drop_duplicates()
             .sort_values(['Field', 'Case']))

    if pairs.empty:
        st.info("No data available for the selected Field/Case combinations.")
        return

    tab_names = [f"{row['Field']} | {row['Case']}" for _, row in pairs.iterrows()]
    sub_tabs = st.tabs(tab_names)

    for sub_tab, (_, row) in zip(sub_tabs, pairs.iterrows()):
        with sub_tab:
            pair_df = profile_filtered[
                (profile_filtered['Field'] == row['Field'])
                & (profile_filtered['Case'] == row['Case'])
            ][['Date', 'Gas Rate', 'Condensate Rate']].sort_values(by='Date').copy()

            pair_df['Date'] = pair_df['Date'].dt.strftime('%b-%Y')
            st.dataframe(pair_df, use_container_width=True, hide_index=True)


def render_assumption_tab(df_assumption, selected_fields, selected_cases):
    """Renders the Assumption tab with a pivoted comparison table."""
    st.subheader("Case Assumption Comparison")

    # Normalize field names for consistent matching
    df_assumption['Field_Norm'] = df_assumption['Field'].map(normalize_field_name)

    asmp_filtered = df_assumption[
        (df_assumption['Field_Norm'].isin(selected_fields))
        & (df_assumption['Case'].isin(selected_cases))
    ].copy()

    if asmp_filtered.empty:
        st.info("No assumption data available for the selected Field/Case combinations.")
        return

    # Pivot: rows = fields, columns = cases
    asmp_pivot = asmp_filtered.pivot(
        index='Field_Norm', columns='Case', values='Assumption'
    )

    # Reorder rows to follow canonical field order
    present_order = [f for f in FIELD_ORDER if f in asmp_pivot.index]
    asmp_pivot = asmp_pivot.reindex(present_order)
    asmp_pivot.index.name = "Field"

    st.dataframe(asmp_pivot.fillna(''), use_container_width=True)


# ── Page Entry Point ─────────────────────────────────────────
def main():
    """Entry point for the LTP Viewer page."""
    inject_custom_css()

    # Data Loading
    try:
        df_profile, df_assumption = load_all_data('LTPDatabase.xlsx')
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return

    # Sidebar Filters
    selected_fields, actual_fields_to_filter, selected_cases = render_sidebar(df_profile)

    if not selected_fields or not selected_cases:
        st.warning("Please select at least one Field and one Case in the sidebar.")
        return

    # Data Filtering — only show data from 2024 onwards per business requirement
    profile_filtered = df_profile[
        (df_profile['Field'].isin(actual_fields_to_filter))
        & (df_profile['Case'].isin(selected_cases))
        & (df_profile['Date'] >= '2024-01-01')
    ].copy()

    # Normalize field names to canonical form for display consistency
    profile_filtered['Field'] = profile_filtered['Field'].map(normalize_field_name)

    # Central Layout
    tab_profile, tab_table, tab_assumption = st.tabs(["Profile", "Table", "Assumption"])

    with tab_profile:
        render_profile_tab(profile_filtered, selected_fields, selected_cases)

    with tab_table:
        render_table_tab(profile_filtered)

    with tab_assumption:
        render_assumption_tab(df_assumption, selected_fields, selected_cases)


# Called by st.navigation — no __name__ guard needed
main()
