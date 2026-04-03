import streamlit as st
import plotly.express as px
from utils.loader import load_patents
from utils.company_utils import inventor_count_df

df = load_patents()

st.title("Patent Dashboard")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Patents", len(df))
col2.metric("Granted", int(df["is_granted"].sum()) if "is_granted" in df.columns else 0)
col3.metric("Published Applications", int((df["status"] == "Published Application").sum()) if "status" in df.columns else 0)
col4.metric("Countries", int(df["country_name"].nunique()) if "country_name" in df.columns else 0)
col5.metric("Companies", int(df["company"].nunique()) if "company" in df.columns else 0)

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Patents by Filing Year")
    year_counts = df["filing_year"].dropna().astype(int).value_counts().sort_index().reset_index()
    year_counts.columns = ["filing_year", "count"]
    fig = px.line(year_counts, x="filing_year", y="count", markers=True)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Patents by Status")
    status_counts = df["status"].fillna("Unknown").value_counts().reset_index()
    status_counts.columns = ["status", "count"]
    fig = px.pie(status_counts, names="status", values="count")
    st.plotly_chart(fig, use_container_width=True)

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Top Companies")
    company_counts = df["company"].fillna("Unassigned").value_counts().head(15).reset_index()
    company_counts.columns = ["company", "count"]
    fig = px.bar(company_counts.sort_values("count", ascending=True), x="count", y="company", orientation="h")
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Top Assignees")
    assignee_counts = df["assignee"].fillna("Unknown").value_counts().head(15).reset_index()
    assignee_counts.columns = ["assignee", "count"]
    fig = px.bar(assignee_counts.sort_values("count", ascending=True), x="count", y="assignee", orientation="h")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Top Inventors")
inventor_counts = inventor_count_df(df, top_n=20)
if inventor_counts.empty:
    st.info("No inventor data available.")
else:
    fig = px.bar(inventor_counts.sort_values("count", ascending=True), x="count", y="inventor", orientation="h")
    st.plotly_chart(fig, use_container_width=True)
