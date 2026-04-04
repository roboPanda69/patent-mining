import pandas as pd
import plotly.express as px
import streamlit as st

from utils.loader import load_patents
from utils.ui_helpers import clean_named_series, top_known_value

st.title("Patent Portfolio Insights")
st.caption("A storytelling view of the patent portfolio for employees and stakeholders.")

df = load_patents().copy()

st.sidebar.header("Insights Filters")
company_options = ["All"] + sorted(df["company"].dropna().astype(str).unique().tolist()) if "company" in df.columns else ["All"]
country_options = ["All"] + sorted(df["country_name"].dropna().astype(str).unique().tolist())
status_options = ["All"] + sorted(df["status"].dropna().astype(str).unique().tolist())
year_options = sorted(df["filing_year"].dropna().astype(int).unique().tolist())

selected_company = st.sidebar.selectbox("Company", company_options)
selected_country = st.sidebar.selectbox("Country / Jurisdiction", country_options)
selected_status = st.sidebar.selectbox("Status", status_options)
selected_years = st.sidebar.multiselect("Filing Year", year_options)

filtered = df.copy()
if selected_company != "All" and "company" in filtered.columns:
    filtered = filtered[filtered["company"] == selected_company]
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
granted_count = int(filtered["is_granted"].sum()) if "is_granted" in filtered.columns else 0
published_count = int(filtered["is_published"].sum()) if "is_published" in filtered.columns else 0
countries_count = int(clean_named_series(filtered["country_name"]).nunique())
inventors_count = int(clean_named_series(filtered["inventor"]).nunique())

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Patents", total_patents)
c2.metric("Granted", granted_count)
c3.metric("Published Applications", published_count)
c4.metric("Countries", countries_count)
c5.metric("Inventors", inventors_count)

st.divider()

top_country, top_country_count = top_known_value(filtered["country_name"])
top_assignee, top_assignee_count = top_known_value(filtered["assignee"])
top_inventor, top_inventor_count = top_known_value(filtered["inventor"])
latest_year = int(filtered["filing_year"].dropna().max()) if filtered["filing_year"].dropna().any() else None

st.subheader("Portfolio Summary")
st.info(
    f"In the current filtered portfolio, the strongest jurisdiction is **{top_country}** with **{top_country_count} patents**. "
    f"The most active assignee is **{top_assignee}** with **{top_assignee_count} patents**, and the strongest named inventor presence is "
    f"**{top_inventor}** with **{top_inventor_count} patents**."
    + (f" The latest filing year visible in this view is **{latest_year}**." if latest_year else "")
)

left, right = st.columns(2)
with left:
    st.subheader("Filing Trend Over Time")
    filing_counts = filtered["filing_year"].dropna().astype(int).value_counts().sort_index().reset_index()
    filing_counts.columns = ["filing_year", "count"]
    fig = px.line(filing_counts, x="filing_year", y="count", markers=True,
                  labels={"filing_year": "Filing Year", "count": "Patent Count"})
    st.plotly_chart(fig, use_container_width=True, key="insights_filing_trend")
with right:
    st.subheader("Portfolio by Status")
    status_counts = filtered["status"].fillna("Unknown").value_counts().reset_index()
    status_counts.columns = ["status", "count"]
    fig = px.pie(status_counts, names="status", values="count")
    st.plotly_chart(fig, use_container_width=True, key="insights_status_mix")

left, right = st.columns(2)
with left:
    st.subheader("Top Countries / Jurisdictions")
    country_counts = clean_named_series(filtered["country_name"]).value_counts().head(12).sort_values(ascending=True).reset_index()
    country_counts.columns = ["country_name", "count"]
    fig = px.bar(country_counts, x="count", y="country_name", orientation="h",
                 labels={"count": "Patent Count", "country_name": "Country / Jurisdiction"})
    st.plotly_chart(fig, use_container_width=True, key="insights_top_countries")
with right:
    st.subheader("Top Assignees")
    assignee_counts = clean_named_series(filtered["assignee"]).value_counts().head(12).sort_values(ascending=True).reset_index()
    assignee_counts.columns = ["assignee", "count"]
    fig = px.bar(assignee_counts, x="count", y="assignee", orientation="h",
                 labels={"count": "Patent Count", "assignee": "Assignee"})
    st.plotly_chart(fig, use_container_width=True, key="insights_top_assignees")

st.subheader("Latest Filing Candidates")
latest = filtered.copy()
if "filing_date" in latest.columns:
    latest = latest.sort_values(by="filing_date", ascending=False)
show_cols = ["patent_id", "title", "company", "assignee", "country_name", "filing_date", "status"]
show_cols = [c for c in show_cols if c in latest.columns]
if "filing_date" in latest.columns:
    latest = latest.copy()
    latest["filing_date"] = pd.to_datetime(latest["filing_date"], errors="coerce").dt.strftime("%d-%m-%Y")
st.dataframe(latest[show_cols].head(25), use_container_width=True, hide_index=True, height=420)

if "patent_id" in latest.columns:
    patent_options = latest["patent_id"].dropna().astype(str).head(25).tolist()
    if patent_options:
        selected_patent = st.selectbox("Open patent detail", patent_options, key="insights_open_patent")
        if st.button("Open Patent Detail", key="insights_open_patent_btn"):
            st.session_state["selected_patent_id"] = selected_patent
            st.switch_page("pages/patent_detail.py")
