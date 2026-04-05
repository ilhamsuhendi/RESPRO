"""
fc_viewer.py — Gas Production FC (Forecast Case) Viewer

Displays monthly gas and condensate production profiles as stacked bar charts
with comparison line overlays. The last selected case (in canonical order) is
rendered as the stacked baseline; preceding cases are overlaid as total lines.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Constants ────────────────────────────────────────────────
# Canonical ordering ensures visual consistency across sessions.
CASE_DISPLAY_ORDER = ["BDG", "FC1", "FC2", "FC3"]
FIELD_DISPLAY_ORDER = ['JKK', 'MKS', 'MKSE', 'MAHA', 'BKA', 'WSN']
BAR_COLORS = ['#117EA8', '#99DAF4', '#FFC000', '#FFEB99', '#767676', '#BFBFBF']
LINE_COLORS = ['#000000', '#FF0000', '#0000FF', '#00FF00', '#FF00FF', '#00FFFF']


# ── Styling ──────────────────────────────────────────────────
def inject_custom_css():
    """Injects CSS for premium tab typography and branded accent color."""
    st.markdown("""
    <style>
    /* Main Tabs and Nested Tabs */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 22px !important;
        font-weight: bold !important;
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
def load_data():
    """Loads profile and assumption sheets from the FCDatabase Excel file."""
    df_profile = pd.read_excel('FCDatabase.xlsx', sheet_name='Profile')
    df_assumptions = pd.read_excel(
        'FCDatabase.xlsx', sheet_name='Assumption',
        usecols=['Field', 'Case', 'Assumption']
    )
    return df_profile, df_assumptions


# ── Helpers ──────────────────────────────────────────────────
def sort_with_preferred_order(items, preferred_order):
    """
    Returns items sorted so that those in `preferred_order` come first
    (in that order), followed by any remaining items in original order.
    """
    ordered = [x for x in preferred_order if x in items]
    ordered += [x for x in items if x not in ordered]
    return ordered


# ── Sidebar Filters ──────────────────────────────────────────
def render_sidebar_filters(df_profile):
    """
    Renders year, case, and field filter controls in the sidebar.

    Returns:
        tuple: (selected_year, df_profile_year, selected_cases,
                selected_fields, sorted_selected_cases)
    """
    # Year filter
    available_years = sorted(df_profile['Date'].dt.year.unique(), reverse=True)
    selected_year = st.sidebar.selectbox("Select Year", available_years)
    df_profile_year = df_profile[df_profile['Date'].dt.year == selected_year]

    # Field filter — rendered first for visual priority
    st.sidebar.subheader("Fields")
    available_fields = df_profile_year['Field'].dropna().unique()
    selected_fields = []
    for f in available_fields:
        if st.sidebar.checkbox(f"{f}", value=True):
            selected_fields.append(f)

    # Case filter — checkboxes in canonical order
    st.sidebar.subheader("Cases")
    available_cases = df_profile_year['Case'].dropna().unique()
    sorted_cases = sort_with_preferred_order(available_cases, CASE_DISPLAY_ORDER)

    selected_cases = []
    for c in sorted_cases:
        if st.sidebar.checkbox(f"{c}", value=True):
            selected_cases.append(c)

    # Validation gates
    if not selected_fields:
        st.warning("Please select at least one Field.")
        st.stop()
    if not selected_cases:
        st.warning("Please select at least one Case.")
        st.stop()

    # Preserve canonical case order among user selections
    sorted_selected_cases = [c for c in sorted_cases if c in selected_cases]

    return (selected_year, df_profile_year, selected_cases,
            selected_fields, sorted_selected_cases)


# ── Visualization ────────────────────────────────────────────
def render_profile(df_filtered, rate_column, title_prefix, decimal_places,
                   selected_year, sorted_selected_cases):
    """
    Renders a combined stacked-bar + line chart with a synchronized data table.

    The *last* case in sorted_selected_cases is the stacked baseline;
    all preceding cases are overlaid as aggregate total lines.
    """
    if df_filtered.empty:
        st.warning("No data available for the selected Field and Case combinations.")
        return

    # Determine stacked vs. line cases
    stacked_case = sorted_selected_cases[-1]
    line_cases = sorted_selected_cases[:-1]

    # Time axis setup
    all_dates = sorted(df_filtered['Date'].dropna().unique())
    date_str_list = [pd.to_datetime(d).strftime('%b') for d in all_dates]
    days_in_period = pd.Series(all_dates).dt.days_in_month.values
    total_days = days_in_period.sum()

    # X-axis: monthly abbreviations + annual weighted-average column
    chart_labels = date_str_list + [str(selected_year)]
    table_header = ['Field / Case'] + chart_labels
    table_cells = []

    # Chart on top, table on bottom
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        specs=[[{"type": "xy"}], [{"type": "table"}]]
    )

    # ── Stacked bar traces (baseline case) ──
    df_stacked = df_filtered[df_filtered['Case'] == stacked_case]
    pivot_stacked = pd.pivot_table(
        df_stacked, index='Date', columns='Field',
        values=rate_column, aggfunc='sum'
    )
    pivot_stacked = pivot_stacked.reindex(all_dates).fillna(0)

    available_fields_in_chart = list(pivot_stacked.columns)
    fields_in_chart = sort_with_preferred_order(
        available_fields_in_chart, FIELD_DISPLAY_ORDER
    )

    for i, field in enumerate(fields_in_chart):
        field_vals = pivot_stacked[field].values
        # Weighted average accounts for unequal month lengths
        avg_val = (field_vals * days_in_period).sum() / total_days if total_days > 0 else 0
        y_with_avg = list(field_vals) + [avg_val]

        fig.add_trace(
            go.Bar(
                x=chart_labels, y=y_with_avg,
                name=f"{field} ({stacked_case})",
                marker_color=BAR_COLORS[i % len(BAR_COLORS)]
            ),
            row=1, col=1
        )
        row_data = ([f"{field} ({stacked_case})"]
                    + [f"{val:.{decimal_places}f}" for val in field_vals]
                    + [f"{avg_val:.{decimal_places}f}"])
        table_cells.append(row_data)

    # ── Line traces (comparison cases) ──
    for i, l_case in enumerate(line_cases):
        df_line = df_filtered[df_filtered['Case'] == l_case]
        line_agg = df_line.groupby('Date')[rate_column].sum()
        line_agg = line_agg.reindex(all_dates).fillna(0)

        line_vals = line_agg.values
        avg_line_val = (line_vals * days_in_period).sum() / total_days if total_days > 0 else 0
        y_line_with_avg = list(line_vals) + [avg_line_val]

        fig.add_trace(
            go.Scatter(
                x=chart_labels, y=y_line_with_avg,
                name=f"{l_case} (Total)",
                mode='lines+markers',
                marker_color=LINE_COLORS[i % len(LINE_COLORS)],
                line=dict(width=2)
            ),
            row=1, col=1
        )
        row_data = ([f"{l_case} (Total)"]
                    + [f"{val:.{decimal_places}f}" for val in line_vals]
                    + [f"{avg_line_val:.{decimal_places}f}"])
        table_cells.append(row_data)

    # Chart styling
    fig.update_layout(
        barmode='stack',
        title_text=f"Monthly {title_prefix} Production Profile",
        title_font_size=25, font_size=17,
        legend_font_size=17, bargap=0.4
    )
    fig.update_xaxes(type='category', tickfont_size=17)
    fig.update_yaxes(tickfont_size=17)

    # Synchronized data table
    col_values = []
    if table_cells:
        col_values.append([row[0] for row in table_cells])
        for col_idx in range(1, len(chart_labels) + 1):
            col_values.append([row[col_idx] for row in table_cells])

    fig.add_trace(
        go.Table(
            header=dict(values=table_header, fill_color='paleturquoise',
                        align='center', font=dict(size=14)),
            cells=dict(values=col_values, fill_color='lavender',
                       align='center', font=dict(size=14))
        ),
        row=2, col=1
    )

    fig.update_layout(height=800)
    st.plotly_chart(fig, use_container_width=True)


def render_assumption_tab(df_assumptions, selected_cases, selected_fields,
                          sorted_selected_cases):
    """
    Renders the Assumption comparison table: rows = fields, columns = cases,
    both following canonical display order.
    """
    st.subheader("Assumptions Comparison")

    df_ass_filtered = df_assumptions[
        df_assumptions['Case'].isin(selected_cases)
        & df_assumptions['Field'].isin(selected_fields)
    ].copy()

    if df_ass_filtered.empty:
        st.info("No assumptions available for the selected filters.")
        return

    df_pivot = df_ass_filtered.pivot(
        index='Field', columns='Case', values='Assumption'
    )

    # Maintain canonical ordering for columns and rows
    cols_to_show = [c for c in sorted_selected_cases if c in df_pivot.columns]
    df_pivot = df_pivot[cols_to_show]

    all_available_fields = df_pivot.index.unique()
    final_field_order = sort_with_preferred_order(
        all_available_fields, FIELD_DISPLAY_ORDER
    )
    df_pivot = df_pivot.reindex(final_field_order)

    df_display = df_pivot.reset_index()
    rename_map = {c: f"{c} Assumption" for c in cols_to_show}
    df_display = df_display.rename(columns=rename_map)

    st.dataframe(df_display.fillna("-"), hide_index=True, use_container_width=True)


# ── Page Entry Point ─────────────────────────────────────────
try:
    df_profile, df_assumptions = load_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

(selected_year, df_profile_year, selected_cases,
 selected_fields, sorted_selected_cases) = render_sidebar_filters(df_profile)

inject_custom_css()

df_filtered = df_profile_year[
    df_profile_year['Field'].isin(selected_fields)
    & df_profile_year['Case'].isin(sorted_selected_cases)
]

tab_profile, tab_assumption = st.tabs(["Profile", "Assumption"])

with tab_profile:
    inner_tab_gas, inner_tab_condensate = st.tabs(["Gas", "Condensate"])

    with inner_tab_gas:
        render_profile(df_filtered, 'Gas Rate', 'Gas', 1,
                       selected_year, sorted_selected_cases)

    with inner_tab_condensate:
        render_profile(df_filtered, 'Condensate Rate', 'Condensate', 0,
                       selected_year, sorted_selected_cases)

with tab_assumption:
    render_assumption_tab(df_assumptions, selected_cases, selected_fields,
                          sorted_selected_cases)
