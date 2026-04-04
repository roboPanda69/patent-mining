import pandas as pd
import plotly.express as px
import streamlit as st

from utils.loader import load_patents
from utils.cpc_utils import explode_cpc_sections
from utils.insight_utils import build_portfolio_observations
from utils.ui_helpers import clean_named_series, top_known_value

st.title("Executive Summary")
st.caption("A communication-friendly summary of the patent portfolio for leadership and stakeholders.")

df = load_patents().copy()

st.sidebar.header("Summary Filters")
company_options = ["All"] + sorted(df["company"].dropna().astype(str).unique().tolist()) if "company" in df.columns else ["All"]
country_options = ["All"] + sorted(df["country_name"].dropna().astype(str).unique().tolist()) if "country_name" in df.columns else ["All"]
status_options = ["All"] + sorted(df["status"].dropna().astype(str).unique().tolist()) if "status" in df.columns else ["All"]
year_options = sorted(df["filing_year"].dropna().astype(int).unique().tolist()) if "filing_year" in df.columns else []

selected_company = st.sidebar.selectbox("Company", company_options)
selected_country = st.sidebar.selectbox("Country / Jurisdiction", country_options)
selected_status = st.sidebar.selectbox("Status", status_options)
selected_years = st.sidebar.multiselect("Filing Year", year_options)

filtered = df.copy()
if selected_company != "All" and "company" in filtered.columns:
    filtered = filtered[filtered["company"] == selected_company]
if selected_country != "All" and "country_name" in filtered.columns:
    filtered = filtered[filtered["country_name"] == selected_country]
if selected_status != "All" and "status" in filtered.columns:
    filtered = filtered[filtered["status"] == selected_status]
if selected_years and "filing_year" in filtered.columns:
    filtered = filtered[filtered["filing_year"].isin(selected_years)]

if filtered.empty:
    st.warning("No patents found for the selected filters.")
    st.stop()

total_patents = len(filtered)
granted = int(filtered["is_granted"].sum()) if "is_granted" in filtered.columns else 0
published = int(filtered["is_published"].sum()) if "is_published" in filtered.columns else 0
countries = int(clean_named_series(filtered["country_name"]).nunique()) if "country_name" in filtered.columns else 0
assignees = int(clean_named_series(filtered["assignee"]).nunique()) if "assignee" in filtered.columns else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Patents", total_patents)
c2.metric("Granted", granted)
c3.metric("Published Applications", published)
c4.metric("Countries", countries)
c5.metric("Assignees", assignees)

st.divider()

observations = build_portfolio_observations(filtered)

top_country, top_country_count = top_known_value(filtered["country_name"]) if "country_name" in filtered.columns else ("Unknown", 0)
top_assignee, top_assignee_count = top_known_value(filtered["assignee"]) if "assignee" in filtered.columns else ("Unknown", 0)
status_mix = filtered["status"].fillna("Unknown").value_counts(normalize=True) if "status" in filtered.columns else pd.Series(dtype=float)
dominant_status = status_mix.index[0] if not status_mix.empty else "Unknown"
dominant_status_share = float(status_mix.iloc[0] * 100) if not status_mix.empty else 0.0

st.subheader("Leadership Summary")
st.success(
    f"The current portfolio view contains **{total_patents} patents** with its strongest visible jurisdiction in **{top_country}**. "
    f"The assignee base is led by **{top_assignee}**, and the current lifecycle mix is weighted toward **{dominant_status}** "
    f"at roughly **{dominant_status_share:.1f}%** of the visible set."
)

st.subheader("Key Messages")
for obs in observations[:5]:
    st.info(obs)

left, right = st.columns(2)
with left:
    st.subheader("Jurisdiction Share")
    if "country_name" in filtered.columns and filtered["country_name"].notna().any():
        country_counts = clean_named_series(filtered["country_name"]).value_counts().head(10).reset_index()
        country_counts.columns = ["country_name", "count"]
        fig = px.bar(country_counts, x="country_name", y="count", labels={"country_name": "Country", "count": "Patent Count"})
        st.plotly_chart(fig, use_container_width=True, key="exec_country_share")
with right:
    st.subheader("Status Mix")
    if "status" in filtered.columns and filtered["status"].notna().any():
        status_counts = filtered["status"].fillna("Unknown").value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        fig = px.pie(status_counts, names="status", values="count")
        st.plotly_chart(fig, use_container_width=True, key="exec_status_mix")

left, right = st.columns(2)
with left:
    st.subheader("Filing Activity Over Time")
    if "filing_year" in filtered.columns and filtered["filing_year"].notna().any():
        year_counts = filtered["filing_year"].dropna().astype(int).value_counts().sort_index().reset_index()
        year_counts.columns = ["filing_year", "count"]
        fig = px.line(year_counts, x="filing_year", y="count", markers=True)
        st.plotly_chart(fig, use_container_width=True, key="exec_filing_trend")
with right:
    st.subheader("Top Assignees")
    if "assignee" in filtered.columns and filtered["assignee"].notna().any():
        assignee_counts = clean_named_series(filtered["assignee"]).value_counts().head(10).sort_values(ascending=True).reset_index()
        assignee_counts.columns = ["assignee", "count"]
        fig = px.bar(assignee_counts, x="count", y="assignee", orientation="h")
        st.plotly_chart(fig, use_container_width=True, key="exec_top_assignees")

if "cpc_sections" in filtered.columns:
    cpc_df = explode_cpc_sections(filtered)
    if not cpc_df.empty:
        st.subheader("Technology Mix")
        bucket_counts = cpc_df["cpc_display"].value_counts().head(10).sort_values(ascending=True).reset_index()
        bucket_counts.columns = ["cpc_display", "count"]
        fig = px.bar(bucket_counts, x="count", y="cpc_display", orientation="h")
        st.plotly_chart(fig, use_container_width=True, key="exec_tech_mix")
