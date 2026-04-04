import plotly.express as px
import streamlit as st

from utils.loader import load_patents
from utils.ui_helpers import clean_named_series


df = load_patents().copy()
if "company" in df.columns and (df["company"] == "JLR").any():
    df = df[df["company"] == "JLR"].copy()

st.title("JLR Patent Dashboard")
st.caption("A focused overview of JLR patent activity.")

with st.expander("What is the difference between Granted and Published Applications?"):
    st.write(
        "**Granted** patents are those where the patent office has allowed the invention and issued patent rights. "
        "**Published Applications** are patent applications that have been publicly disclosed but are not yet granted. "
        "Some published applications may later become granted patents, while others may be amended, abandoned, or refused."
    )

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Patents", len(df))
col2.metric("Granted", int(df["is_granted"].sum()) if "is_granted" in df.columns else 0)
col3.metric("Published Applications", int(df["is_published"].sum()) if "is_published" in df.columns else 0)
col4.metric("Countries", int(clean_named_series(df.get("country_name")).nunique()) if "country_name" in df.columns else 0)

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Patents by Filing Year")
    year_counts = (
        df["filing_year"].dropna().astype(int).value_counts().sort_index().reset_index()
    )
    year_counts.columns = ["filing_year", "count"]
    fig = px.line(year_counts, x="filing_year", y="count", markers=True)
    st.plotly_chart(fig, use_container_width=True, key="dashboard_year_trend")

with col_right:
    st.subheader("Patents by Status")
    status_counts = df["status"].fillna("Unknown").value_counts().reset_index()
    status_counts.columns = ["status", "count"]
    fig = px.pie(status_counts, names="status", values="count")
    st.plotly_chart(fig, use_container_width=True, key="dashboard_status_pie")

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Top Countries / Jurisdictions")
    country_counts = clean_named_series(df["country_name"]).value_counts().head(15).sort_values(ascending=True).reset_index()
    country_counts.columns = ["country_name", "count"]
    fig = px.bar(country_counts, x="count", y="country_name", orientation="h")
    st.plotly_chart(fig, use_container_width=True, key="dashboard_top_countries")

with col_right:
    st.subheader("Top Assignees")
    assignee_counts = clean_named_series(df["assignee"]).value_counts().head(15).sort_values(ascending=True).reset_index()
    assignee_counts.columns = ["assignee", "count"]
    fig = px.bar(assignee_counts, x="count", y="assignee", orientation="h")
    st.plotly_chart(fig, use_container_width=True, key="dashboard_top_assignees")

st.subheader("Top Inventors")
inventor_counts = clean_named_series(df["inventor"]).value_counts().head(20).sort_values(ascending=True).reset_index()
inventor_counts.columns = ["inventor", "count"]
fig = px.bar(inventor_counts, x="count", y="inventor", orientation="h")
st.plotly_chart(fig, use_container_width=True, key="dashboard_top_inventors")
