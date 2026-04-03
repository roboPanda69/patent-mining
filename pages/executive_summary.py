import streamlit as st
from utils.loader import load_patents
from utils.company_utils import get_company_options, filter_by_company
from utils.insight_utils import build_portfolio_observations

st.title("Executive Summary")
st.caption("Leadership-friendly narrative summary of the current patent view.")

df = load_patents().copy()
st.sidebar.header("Summary Filters")
company_options = get_company_options(df, include_all=True)
selected_companies = st.sidebar.multiselect("Company", company_options, default=["All"])
filtered = filter_by_company(df, selected_companies)

if filtered.empty:
    st.warning("No patents found for the selected filters.")
    st.stop()

observations = build_portfolio_observations(filtered)
for obs in observations:
    st.info(obs)

st.subheader("Why this matters to JLR")
company_counts = filtered["company"].fillna("Unassigned").value_counts()
if "JLR" in company_counts.index:
    jlr_share = 100.0 * company_counts["JLR"] / max(int(company_counts.sum()), 1)
    st.markdown("- JLR represents **%.1f%%** of the current filtered view, so changes in this slice can be read against the wider competitive context." % jlr_share)
if "top_level_tech" in filtered.columns:
    tech_counts = filtered["top_level_tech"].fillna("Other / Unmapped").value_counts()
    if not tech_counts.empty:
        st.markdown("- The most visible technology area is **%s**, which can guide where leadership may want deeper portfolio review." % tech_counts.idxmax())
if "company" in filtered.columns and filtered["company"].nunique() > 1:
    st.markdown("- Because multiple companies are visible here, this summary can be used not only for portfolio tracking but also for competitor positioning discussions.")
