import streamlit as st
from utils.loader import load_patents
from utils.company_utils import get_company_options

df = load_patents()
st.title("Patent Explorer")
st.sidebar.header("Filters")

company_options = get_company_options(df, include_all=False)
selected_companies = st.sidebar.multiselect("Company", company_options)
years = sorted(df["filing_year"].dropna().astype(int).unique().tolist())
selected_years = st.sidebar.multiselect("Filing Year", years)
countries = sorted(df["country_name"].dropna().astype(str).unique().tolist())
selected_countries = st.sidebar.multiselect("Country / Jurisdiction", countries)
statuses = sorted(df["status"].dropna().astype(str).unique().tolist())
selected_statuses = st.sidebar.multiselect("Status", statuses)
assignee_query = st.sidebar.text_input("Assignee contains")
inventor_query = st.sidebar.text_input("Inventor contains")
title_query = st.sidebar.text_input("Title contains")

filtered = df.copy()
if selected_companies:
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

st.write("Showing %s patents" % len(filtered))
show_cols = ["patent_id", "title", "company", "assignee", "inventor", "country_name", "filing_year", "status", "top_level_tech", "result_link"]
show_cols = [c for c in show_cols if c in filtered.columns]
st.dataframe(filtered[show_cols], use_container_width=True)
