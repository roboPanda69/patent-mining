import streamlit as st
import pandas as pd
import plotly.express as px
from utils.loader import load_patents
from utils.company_utils import get_company_options, filter_by_company, inventor_count_df, top_inventor_summary, format_date_ddmmyyyy

st.title("Patent Portfolio Insights")
st.caption("A storytelling view of the patent portfolio for employees and stakeholders.")

df = load_patents().copy()
st.sidebar.header("Insights Filters")
company_options = get_company_options(df, include_all=True)
country_options = ["All"] + sorted(df["country_name"].dropna().astype(str).unique().tolist())
status_options = ["All"] + sorted(df["status"].dropna().astype(str).unique().tolist())
year_options = sorted(df["filing_year"].dropna().astype(int).unique().tolist())

selected_companies = st.sidebar.multiselect("Company", company_options, default=["All"])
selected_country = st.sidebar.selectbox("Country / Jurisdiction", country_options)
selected_status = st.sidebar.selectbox("Status", status_options)
selected_years = st.sidebar.multiselect("Filing Year", year_options)

filtered = filter_by_company(df, selected_companies)
if selected_country != "All":
    filtered = filtered[filtered["country_name"] == selected_country]
if selected_status != "All":
    filtered = filtered[filtered["status"] == selected_status]
if selected_years:
    filtered = filtered[filtered["filing_year"].isin(selected_years)]

if filtered.empty:
    st.warning("No patents found for the selected filters.")
    st.stop()

total_patents = len(filtered)
granted_count = int((filtered["status"] == "Granted").sum())
published_count = int((filtered["status"] == "Published Application").sum())
countries_count = int(filtered["country_name"].nunique())
inventors_count = int(inventor_count_df(filtered, top_n=999)["inventor"].nunique()) if not inventor_count_df(filtered, top_n=999).empty else 0
companies_count = int(filtered["company"].nunique())

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Patents", total_patents)
c2.metric("Granted", granted_count)
c3.metric("Published Applications", published_count)
c4.metric("Countries", countries_count)
c5.metric("Inventors", inventors_count)
c6.metric("Companies", companies_count)

st.divider()

top_country = filtered["country_name"].fillna("Unknown").value_counts().idxmax()
top_country_count = int(filtered["country_name"].fillna("Unknown").value_counts().max())
top_assignee = filtered["assignee"].fillna("Unknown").value_counts().idxmax()
top_assignee_count = int(filtered["assignee"].fillna("Unknown").value_counts().max())
top_inventor, top_inventor_count = top_inventor_summary(filtered)
latest_year = int(filtered["filing_year"].dropna().max()) if filtered["filing_year"].dropna().any() else None

summary_text = (
    "In the current filtered portfolio, the strongest jurisdiction is **%s** with **%s patents**. "
    "The most active assignee is **%s** with **%s patents**."
    % (top_country, top_country_count, top_assignee, top_assignee_count)
)
if top_inventor:
    summary_text += " The most frequent named inventor is **%s** with **%s patents**." % (top_inventor, top_inventor_count)
if latest_year:
    summary_text += " The latest filing year visible in this view is **%s**." % latest_year
st.subheader("Portfolio Summary")
st.info(summary_text)

left, right = st.columns(2)
with left:
    st.subheader("Filing Trend Over Time")
    filing_counts = filtered["filing_year"].dropna().astype(int).value_counts().sort_index().reset_index()
    filing_counts.columns = ["filing_year", "count"]
    fig = px.line(filing_counts, x="filing_year", y="count", markers=True, labels={"filing_year": "Filing Year", "count": "Patent Count"})
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("Portfolio by Status")
    status_counts = filtered["status"].fillna("Unknown").value_counts().reset_index()
    status_counts.columns = ["status", "count"]
    fig = px.pie(status_counts, names="status", values="count")
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("Top Countries / Jurisdictions")
    country_counts = filtered["country_name"].fillna("Unknown").value_counts().head(12).reset_index()
    country_counts.columns = ["country_name", "count"]
    fig = px.bar(country_counts.sort_values("count", ascending=True), x="count", y="country_name", orientation="h", labels={"count": "Patent Count", "country_name": "Country / Jurisdiction"})
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("Top Assignees")
    assignee_counts = filtered["assignee"].fillna("Unknown").value_counts().head(12).reset_index()
    assignee_counts.columns = ["assignee", "count"]
    fig = px.bar(assignee_counts.sort_values("count", ascending=True), x="count", y="assignee", orientation="h", labels={"count": "Patent Count", "assignee": "Assignee"})
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Top Companies")
company_counts = filtered["company"].fillna("Unassigned").value_counts().head(12).reset_index()
company_counts.columns = ["company", "count"]
fig = px.bar(company_counts.sort_values("count", ascending=True), x="count", y="company", orientation="h", labels={"count": "Patent Count", "company": "Company"})
st.plotly_chart(fig, use_container_width=True)

st.subheader("Country vs Filing Year Heatmap")
heatmap_df = filtered.dropna(subset=["country_name", "filing_year"]).copy()
heatmap_df["filing_year"] = heatmap_df["filing_year"].astype(int)
heatmap_counts = heatmap_df.groupby(["country_name", "filing_year"]).size().reset_index(name="count")
if not heatmap_counts.empty:
    fig = px.density_heatmap(heatmap_counts, x="filing_year", y="country_name", z="count", histfunc="sum", labels={"filing_year": "Filing Year", "country_name": "Country / Jurisdiction", "count": "Patent Count"})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Not enough country/year data to build the heatmap.")

st.subheader("Top Inventors")
inventor_counts = inventor_count_df(filtered, top_n=15)
if inventor_counts.empty:
    st.info("No inventor data available.")
else:
    fig = px.bar(inventor_counts.sort_values("count", ascending=True), x="count", y="inventor", orientation="h", labels={"count": "Patent Count", "inventor": "Inventor"})
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Latest Filing Candidates")
latest_patents = filtered.sort_values(by=["filing_date", "publication_date", "priority_date"], ascending=False).head(200).copy()
if "filing_date" in latest_patents.columns:
    latest_patents["filing_date"] = latest_patents["filing_date"].apply(format_date_ddmmyyyy)
show_cols = ["patent_id", "title", "company", "assignee", "inventor", "country_name", "filing_date", "status", "top_level_tech"]
show_cols = [c for c in show_cols if c in latest_patents.columns]
st.dataframe(latest_patents[show_cols], use_container_width=True, height=420)
