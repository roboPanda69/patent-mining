import streamlit as st

from utils.loader import load_patents
from utils.ui_helpers import clickable_patent_table


df = load_patents().copy()

st.title("Patent Explorer")
st.sidebar.header("Filters")

company_options = sorted(df["company"].dropna().astype(str).unique()) if "company" in df.columns else []
years = sorted(df["filing_year"].dropna().unique())
countries = sorted(df["country_name"].dropna().astype(str).unique())
statuses = sorted(df["status"].dropna().astype(str).unique())

selected_companies = st.sidebar.multiselect("Company", company_options)
selected_years = st.sidebar.multiselect("Filing Year", years)
selected_countries = st.sidebar.multiselect("Country / Jurisdiction", countries)
selected_statuses = st.sidebar.multiselect("Status", statuses)
assignee_query = st.sidebar.text_input("Assignee contains")
inventor_query = st.sidebar.text_input("Inventor contains")
title_query = st.sidebar.text_input("Title contains")

filtered = df.copy()
if selected_companies and "company" in filtered.columns:
    filtered = filtered[filtered["company"].isin(selected_companies)]
if selected_years:
    filtered = filtered[filtered["filing_year"].isin(selected_years)]
if selected_countries:
    filtered = filtered[filtered["country_name"].isin(selected_countries)]
if selected_statuses:
    filtered = filtered[filtered["status"].isin(selected_statuses)]
if assignee_query:
    filtered = filtered[filtered["assignee"].fillna("").str.contains(assignee_query, case=False)]
if inventor_query:
    filtered = filtered[filtered["inventor"].fillna("").str.contains(inventor_query, case=False)]
if title_query:
    filtered = filtered[filtered["title"].fillna("").str.contains(title_query, case=False)]

st.write(f"Showing {len(filtered)} patents")
clickable_patent_table(
    filtered,
    title="Patent Table",
    key_prefix="explorer",
    show_cols=[
        "patent_id", "title", "company", "assignee", "inventor",
        "country_name", "filing_year", "status", "result_link"
    ],
    height=520,
)
