import streamlit as st
import plotly.express as px
from utils.loader import load_patents
from utils.company_utils import get_company_options
from utils.competitor_analytics import company_summary, recent_growth_summary, technology_distribution, company_technology_heatmap, company_deep_dive, overlap_unique_tech, competitor_insight_lines

st.title("Competitor Intelligence")
st.caption("Integrated comparison view for JLR and competitor patent portfolios.")

df = load_patents().copy()
company_options = [c for c in get_company_options(df, include_all=False) if c != "Unassigned"]

if df.empty or not company_options:
    st.warning("No company-tagged patents are available.")
    st.stop()

mode = st.radio("Section", ["Executive Overview", "Company Deep Dive", "JLR vs Selected Competitor", "Technology Comparison"], horizontal=True)

if mode == "Executive Overview":
    counts = company_summary(df)
    growth = recent_growth_summary(df)
    tech = technology_distribution(df)
    jlr_tech = None
    jlr_slice = df[df["company"] == "JLR"]
    if not jlr_slice.empty and "top_level_tech" in jlr_slice.columns:
        tmp = jlr_slice["top_level_tech"].fillna("Other / Unmapped").value_counts()
        if not tmp.empty:
            jlr_tech = (tmp.idxmax(), int(tmp.max()))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Companies", int(df["company"].nunique()))
    c2.metric("Visible Patents", len(df))
    c3.metric("Fastest Recent Grower", growth[0] if growth else "N/A")
    c4.metric("JLR Strongest Tech", jlr_tech[0] if jlr_tech else "N/A")

    for line in competitor_insight_lines(df):
        st.info(line)

    fig = px.bar(counts.sort_values("count", ascending=True), x="count", y="company", orientation="h", title="Total Patents by Company")
    st.plotly_chart(fig, use_container_width=True)

    trend = df.dropna(subset=["filing_year"]).copy()
    trend["filing_year"] = trend["filing_year"].astype(int)
    trend_counts = trend.groupby(["filing_year", "company"]).size().reset_index(name="count")
    fig = px.line(trend_counts, x="filing_year", y="count", color="company", markers=True, title="Year-wise Filing Trend by Company")
    st.plotly_chart(fig, use_container_width=True)

    tech_company = df.groupby(["company", "top_level_tech"]).size().reset_index(name="count")
    fig = px.bar(tech_company, x="company", y="count", color="top_level_tech", title="Technology Distribution by Company")
    st.plotly_chart(fig, use_container_width=True)

    heat = company_technology_heatmap(df)
    fig = px.density_heatmap(heat, x="top_level_tech", y="company", z="count", histfunc="sum", title="Company vs Technology Heatmap")
    st.plotly_chart(fig, use_container_width=True)

elif mode == "Company Deep Dive":
    company = st.selectbox("Select company", company_options)
    deep = company_deep_dive(df, company)
    working = deep["df"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Patents", len(working))
    c2.metric("Countries", int(working["country_name"].nunique()) if "country_name" in working.columns else 0)
    c3.metric("Technology Areas", int(working["top_level_tech"].nunique()) if "top_level_tech" in working.columns else 0)

    trend = working.dropna(subset=["filing_year"]).copy()
    if not trend.empty:
        trend["filing_year"] = trend["filing_year"].astype(int)
        trend_counts = trend["filing_year"].value_counts().sort_index().reset_index()
        trend_counts.columns = ["filing_year", "count"]
        fig = px.line(trend_counts, x="filing_year", y="count", markers=True, title="Filing Trend Over Time")
        st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top Inventors")
        st.dataframe(deep["inventors"], use_container_width=True, height=320)
    with col2:
        st.subheader("Top CPC Classes")
        st.dataframe(deep["cpc"], use_container_width=True, height=320)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top Technology Areas")
        st.dataframe(deep["tech"], use_container_width=True, height=320)
    with col2:
        st.subheader("Major Patent Themes / Keywords")
        st.dataframe(deep["keywords"], use_container_width=True, height=320)

elif mode == "JLR vs Selected Competitor":
    competitor = st.selectbox("Select competitor", [c for c in company_options if c != "JLR"])
    compare_df = df[df["company"].isin(["JLR", competitor])].copy()

    c1, c2 = st.columns(2)
    c1.metric("JLR Patents", len(compare_df[compare_df["company"] == "JLR"]))
    c2.metric("%s Patents" % competitor, len(compare_df[compare_df["company"] == competitor]))

    trend = compare_df.dropna(subset=["filing_year"]).copy()
    if not trend.empty:
        trend["filing_year"] = trend["filing_year"].astype(int)
        trend_counts = trend.groupby(["filing_year", "company"]).size().reset_index(name="count")
        fig = px.line(trend_counts, x="filing_year", y="count", color="company", markers=True, title="Year-wise Trend Comparison")
        st.plotly_chart(fig, use_container_width=True)

    tech = compare_df.groupby(["company", "top_level_tech"]).size().reset_index(name="count")
    fig = px.bar(tech, x="top_level_tech", y="count", color="company", barmode="group", title="Technology Split Comparison")
    st.plotly_chart(fig, use_container_width=True)

    overlap = overlap_unique_tech(compare_df, "JLR", competitor)
    st.subheader("Overlap vs Unique Technology Areas")
    a, b, c = st.columns(3)
    a.markdown("**Overlap**")
    a.write(overlap["overlap"] or ["None"])
    b.markdown("**JLR Only**")
    b.write(overlap["left_only"] or ["None"])
    c.markdown("**%s Only**" % competitor)
    c.write(overlap["right_only"] or ["None"])

elif mode == "Technology Comparison":
    tech_options = sorted(df["top_level_tech"].fillna("Other / Unmapped").astype(str).unique().tolist())
    selected_tech = st.selectbox("Technology area", tech_options)
    working = df[df["top_level_tech"] == selected_tech].copy()

    st.info("This view compares which companies are most visible in **%s** and how activity is evolving over time." % selected_tech)

    company_counts = working["company"].fillna("Unassigned").value_counts().reset_index()
    company_counts.columns = ["company", "count"]
    fig = px.bar(company_counts.sort_values("count", ascending=True), x="count", y="company", orientation="h", title="Companies strongest in selected technology")
    st.plotly_chart(fig, use_container_width=True)

    trend = working.dropna(subset=["filing_year"]).copy()
    if not trend.empty:
        trend["filing_year"] = trend["filing_year"].astype(int)
        trend_counts = trend.groupby(["filing_year", "company"]).size().reset_index(name="count")
        fig = px.line(trend_counts, x="filing_year", y="count", color="company", markers=True, title="Recent trend in selected technology")
        st.plotly_chart(fig, use_container_width=True)

    top_patents = working.sort_values(by=["filing_year", "publication_year"], ascending=[False, False]).head(20)
    show_cols = [c for c in ["patent_id", "title", "company", "assignee", "filing_year", "country_name"] if c in top_patents.columns]
    st.subheader("Top patents in this technology")
    st.dataframe(top_patents[show_cols], use_container_width=True, height=320)
