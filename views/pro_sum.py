"""
pro_sum.py — Production Profile Summary Dashboard

Provides an executive-level view of production data: a summary table with
EUR (Estimated Ultimate Recovery) and RF (Recovery Factor) calculations,
yearly bar charts for Gas and Condensate rates, and per-field/case detail tables.
"""

import streamlit as st
import pandas as pd
import plotly.express as px


# ── Styling ──────────────────────────────────────────────────
def inject_custom_css():
    """
    Applies custom CSS for a polished, premium dashboard look.
    Typography, tabs, checkboxes, and sidebar are all scaled and
    styled for consistency across the RESPRO suite.
    """
    st.markdown("""
    <style>
        /* Main container padding */
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }

        /* Increase font size in main content area only (not sidebar) */
        .block-container [data-testid="stMarkdownContainer"] {
            font-size: 1.15rem !important;
        }

        /* Ensure tabs follow the same scaling */
        div[data-testid="stTabs"] button [data-testid="stMarkdownContainer"] p {
            font-size: 1.2rem !important;
            font-weight: 600 !important;
        }

        /* Selected tab styling */
        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: #117EA8 !important;
            border-bottom-color: #117EA8 !important;
        }

        /* Checkbox styling */
        div[data-testid="stCheckbox"] div[role="checkbox"][aria-checked="true"] {
            background-color: #117EA8 !important;
            border-color: #117EA8 !important;
        }

        /* Hover effects for a premium feel */
        div[data-testid="stTabs"] button:hover {
            color: #117EA8 !important;
            background-color: rgba(17, 126, 168, 0.05) !important;
        }
    </style>
    """, unsafe_allow_html=True)


# ── Data Loading ─────────────────────────────────────────────
def get_days_in_year(year):
    """
    Returns the number of days in a given year (365 or 366).
    Used for EUR volumetric calculations (daily rate → yearly volume).
    """
    try:
        return 366 if pd.Timestamp(int(year), 1, 1).is_leap_year else 365
    except:
        return 365


@st.cache_data
def load_data(file_path):
    """
    Loads Profile and Assumption sheets from the Excel database.

    Args:
        file_path: Path to the Excel file.
    Returns:
        tuple: (profile_df, assumption_df) DataFrames.
    """
    profile_df = pd.read_excel(file_path, sheet_name='Profile')
    assumption_df = pd.read_excel(file_path, sheet_name='Assumption')
    return profile_df, assumption_df


# ── Business Logic ───────────────────────────────────────────
def calculate_eur_summary(filtered_profile):
    """
    Calculates Estimated Ultimate Recovery (EUR) for Gas and Condensate
    by field/case grouping using sumproduct of rate × days.

    Gas EUR is expressed in Bcf (rate × days / 1000).
    Condensate EUR is expressed in MMbbl (rate × days / 1,000,000).

    Args:
        filtered_profile: DataFrame with a pre-computed 'Days' column.
    Returns:
        DataFrame: Summary with Gas EUR and Condensate EUR per Field/Case.
    """
    summary_data = []
    for (field, case), group in filtered_profile.groupby(['Field', 'Case']):
        gas_eur_bcf = (group['Gas Rate'] * group['Days']).sum() / 1000
        cond_eur_mmbbl = (group['Condensate Rate'] * group['Days']).sum() / 1000000

        summary_data.append({
            'Field': field,
            'Case': case,
            'Gas EUR, Bcf': gas_eur_bcf,
            'Condensate EUR, MMbbl': cond_eur_mmbbl
        })

    return pd.DataFrame(summary_data)


def build_final_summary_table(calc_df, assumption_df):
    """
    Merges EUR calculations with assumption metadata and computes
    the Gas Recovery Factor (RF = Gas EUR in Tcf / GIIP × 100).

    Args:
        calc_df: DataFrame from calculate_eur_summary().
        assumption_df: Raw assumption DataFrame.
    Returns:
        DataFrame: Final display-ready summary table.
    """
    assumption_df.columns = assumption_df.columns.str.strip()

    if 'Submit Date' not in assumption_df.columns:
        st.error(
            f"Error: Could not find 'Submit Date' in the Assumption sheet.\n\n"
            f"The columns found are: {list(assumption_df.columns)}\n\n"
            f"If you just added it, please try clearing the cache in Streamlit "
            f"(Top Right Menu -> Clear Cache or press 'C')."
        )
        st.stop()

    merged_summary = pd.merge(
        calc_df,
        assumption_df[[
            'Field', 'Case', 'Model Basis & Assumption',
            'Submit Date', 'SU Date', 'GIIP, Tcf'
        ]],
        on=['Field', 'Case'],
        how='left'
    )

    # RF = (EUR in Bcf → Tcf via /1000) / GIIP × 100
    merged_summary['Gas RF'] = (
        (merged_summary['Gas EUR, Bcf'] / 1000)
        / merged_summary['GIIP, Tcf'] * 100
    )

    final_table = merged_summary[[
        'Field', 'Case', 'Model Basis & Assumption', 'Submit Date',
        'SU Date', 'GIIP, Tcf', 'Gas EUR, Bcf',
        'Condensate EUR, MMbbl', 'Gas RF'
    ]]
    return final_table


# ── Sidebar ──────────────────────────────────────────────────
def render_sidebar(profile_df):
    """
    Renders sidebar filter controls for Field and Case selection.

    Default checked fields: Gehem, Geng North.
    Default checked case: FID.

    Returns:
        tuple: (selected_fields, selected_cases)
    """
    # Field selection
    st.sidebar.subheader("Fields")
    fields = sorted(profile_df['Field'].dropna().unique())
    selected_fields = []
    for f in fields:
        if st.sidebar.checkbox(f, value=f in ["Gehem", "Geng North"], key=f"field_{f}"):
            selected_fields.append(f)

    # Case selection
    st.sidebar.subheader("Cases")
    cases = sorted(profile_df['Case'].dropna().unique())
    selected_cases = []
    for c in cases:
        if st.sidebar.checkbox(c, value=c == "FID", key=f"case_{c}"):
            selected_cases.append(c)

    return selected_fields, selected_cases


# ── Visualization ────────────────────────────────────────────
def render_summary_table(final_table):
    """Renders the styled summary table with numeric formatting and alignment."""
    styled_summary = final_table.style.format({
        'GIIP, Tcf': "{:,.2f}",
        'Gas EUR, Bcf': "{:,.2f}",
        'Condensate EUR, MMbbl': "{:,.2f}",
        'Gas RF': "{:,.2f}%",
        'Submit Date': lambda t: t.strftime('%d-%b-%Y') if pd.notnull(t) and type(t) != str else t,
        'SU Date': lambda t: t.strftime('%d-%b-%Y') if pd.notnull(t) and type(t) != str else t
    }).set_properties(
        subset=['GIIP, Tcf', 'Gas EUR, Bcf', 'Condensate EUR, MMbbl', 'Gas RF'],
        **{'text-align': 'center'}
    ).set_table_styles([
        {'selector': 'th', 'props': [('text-align', 'center'), ('font-size', '1.1rem')]},
        {'selector': 'td', 'props': [('font-size', '1.1rem')]}
    ])

    st.dataframe(
        styled_summary,
        use_container_width=True,
        height=200,
        hide_index=True
    )


def render_production_charts(chart_data):
    """Renders Gas and Condensate grouped bar charts in separate tabs."""
    tab_gas, tab_cond = st.tabs(["Gas Production Rate", "Condensate Production Rate"])

    with tab_gas:
        fig_gas = px.bar(
            chart_data, x='Year', y='Gas Rate', color='Field - Case',
            title='Yearly Gas Production Rate',
            labels={'Gas Rate': 'Rate (mmscfd)', 'Year': 'Year'},
            barmode='group'
        )
        if not chart_data.empty:
            fig_gas.update_layout(
                xaxis_title=None, xaxis_type='category',
                font=dict(size=16)
            )
        st.plotly_chart(fig_gas, use_container_width=True)

    with tab_cond:
        fig_cond = px.bar(
            chart_data, x='Year', y='Condensate Rate', color='Field - Case',
            title='Yearly Condensate Production Rate',
            labels={'Condensate Rate': 'Rate (bbl/d)', 'Year': 'Year'},
            barmode='group'
        )
        if not chart_data.empty:
            fig_cond.update_layout(
                xaxis_title=None, xaxis_type='category',
                font=dict(size=16)
            )
        st.plotly_chart(fig_cond, use_container_width=True)


def render_detail_tables(filtered_profile):
    """Renders per-field/case detail tables in separate tabs."""
    detail_table = filtered_profile[
        ['Year', 'Field', 'Case', 'Gas Rate', 'Condensate Rate']
    ].copy()
    detail_table['Field - Case'] = detail_table['Field'] + " - " + detail_table['Case']

    unique_combinations = detail_table['Field - Case'].unique()
    if len(unique_combinations) == 0:
        return

    tabs = st.tabs(list(unique_combinations))

    for tab, combination in zip(tabs, unique_combinations):
        with tab:
            display_df = detail_table[
                detail_table['Field - Case'] == combination
            ][['Year', 'Gas Rate', 'Condensate Rate']]

            st.dataframe(
                display_df.style.format({
                    'Gas Rate': "{:,.2f}",
                    'Condensate Rate': "{:,.2f}"
                }).set_table_styles([
                    {'selector': 'th', 'props': [('font-size', '1.1rem')]},
                    {'selector': 'td', 'props': [('font-size', '1.1rem')]}
                ]),
                use_container_width=True,
                hide_index=True,
                height=450
            )


# ── Page Entry Point ─────────────────────────────────────────
inject_custom_css()

# Data Loading
file_path = 'Profile Summary.xlsx'
try:
    profile_df, assumption_df = load_data(file_path)
except Exception as e:
    st.error(f"Error loading the Excel file: {e}")
    st.stop()

# Sidebar Filters
selected_fields, selected_cases = render_sidebar(profile_df)

# Data Processing
filtered_profile = profile_df[
    (profile_df['Field'].isin(selected_fields))
    & (profile_df['Case'].isin(selected_cases))
].copy()

if filtered_profile.empty:
    st.warning("No data matches the selected filters.")
    st.stop()

# Add days column for EUR volumetric calculations
filtered_profile['Days'] = filtered_profile['Year'].apply(get_days_in_year)

# EUR Calculations & Summary Table
calc_df = calculate_eur_summary(filtered_profile)
final_table = build_final_summary_table(calc_df, assumption_df)

# ── Upper Layout: Summary Table ──
st.header("Summary Table")
render_summary_table(final_table)
st.divider()

# ── Lower Layout: Charts (left) + Detail Tables (right) ──
lower_left_col, lower_right_col = st.columns([3, 1])

with lower_left_col:
    chart_data = filtered_profile.groupby(
        ['Year', 'Field', 'Case']
    )[['Gas Rate', 'Condensate Rate']].sum().reset_index()
    chart_data['Field - Case'] = chart_data['Field'] + " / " + chart_data['Case']
    render_production_charts(chart_data)

with lower_right_col:
    render_detail_tables(filtered_profile)
