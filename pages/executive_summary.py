import streamlit as st
from utils.loader import load_patents
from utils.company_utils import get_company_options, filter_by_company
from utils.insight_utils import build_portfolio_observations, get_top_mapped_technology

st.title("Executive Summary")
st.caption("Leadership-friendly narrative summary of the current patent view.")

df = load_patents().copy()

st.sidebar.header("Summary Filters")
company_options = get_company_options(df, include_all=True)
default_companies = ["JLR"] if "JLR" in company_options else ["All"]
selected_companies = st.sidebar.multiselect("Company", company_options, default=default_companies)
country_options = ["All"] + sorted(df["country_name"].dropna().astype(str).unique().tolist()) if "country_name" in df.columns else ["All"]
status_options = ["All"] + sorted(df["status"].dropna().astype(str).unique().tolist()) if "status" in df.columns else ["All"]
year_options = sorted(df["filing_year"].dropna().astype(int).unique().tolist()) if "filing_year" in df.columns else []

selected_country = st.sidebar.selectbox("Country / Jurisdiction", country_options)
selected_status = st.sidebar.selectbox("Status", status_options)
selected_years = st.sidebar.multiselect("Filing Year", year_options)

filtered = filter_by_company(df, selected_companies)
if selected_country != "All" and "country_name" in filtered.columns:
    filtered = filtered[filtered["country_name"] == selected_country]
if selected_status != "All" and "status" in filtered.columns:
    filtered = filtered[filtered["status"] == selected_status]
if selected_years and "filing_year" in filtered.columns:
    filtered = filtered[filtered["filing_year"].isin(selected_years)]

if filtered.empty:
    st.warning("No patents found for the selected filters.")
    st.stop()

observations = build_portfolio_observations(filtered)
for obs in observations:
    st.info(obs)

st.subheader("Why this matters to JLR")
visible_companies = filtered["company"].fillna("Unassigned").nunique() if "company" in filtered.columns else 0
if visible_companies > 1:
    company_counts = filtered["company"].fillna("Unassigned").value_counts()
    if "JLR" in company_counts.index:
        jlr_share = 100.0 * company_counts["JLR"] / max(int(company_counts.sum()), 1)
        st.markdown("- JLR represents **%.1f%%** of the current filtered view, so this slice can be read against the visible competitive context." % jlr_share)
    st.markdown("- Because multiple companies are visible here, this summary can support both portfolio tracking and competitor positioning discussions.")
else:
    st.markdown("- This summary is currently focused on a single company view, so it is better suited for internal portfolio review than direct competitor comparison.")

if "top_level_tech" in filtered.columns:
    top_tech, _, _, unmapped_share = get_top_mapped_technology(filtered["top_level_tech"])
    if top_tech:
        st.markdown("- The clearest mapped technology signal in this view is **%s**, which is a good candidate for deeper leadership review." % top_tech)
    elif unmapped_share > 0:
        st.markdown("- A noticeable portion of the technology tagging is still unmapped, so leadership should treat the technology summary as an early directional view.")
