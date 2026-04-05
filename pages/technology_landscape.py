import streamlit as st
import plotly.express as px
from utils.loader import load_patents
from utils.company_utils import get_company_options, filter_by_company
from utils.cpc_utils import explode_cpc_sections, summarize_cpc_signal
from utils.ui_helpers import clickable_patent_table, clean_named_series

st.title("Technology Landscape")
st.caption("Analyze patents by CPC technology buckets and company context.")

df = load_patents().copy()
st.sidebar.header("Technology Filters")
company_options = get_company_options(df, include_all=True)
default_companies = ["JLR"] if "JLR" in company_options else ["All"]
selected_companies = st.sidebar.multiselect("Company", company_options, default=default_companies)
country_options = ["All"] + sorted(clean_named_series(df["country_name"], fallback="Unknown").unique().tolist()) if "country_name" in df.columns else ["All"]
status_options = ["All"] + sorted(df["status"].dropna().astype(str).unique().tolist()) if "status" in df.columns else ["All"]
year_options = sorted(df["filing_year"].dropna().astype(int).unique().tolist()) if "filing_year" in df.columns else []
patent_type_options = ["All"] + sorted(df["patent_type"].dropna().astype(str).unique().tolist()) if "patent_type" in df.columns else ["All"]

selected_country = st.sidebar.selectbox("Country / Jurisdiction", country_options)
selected_status = st.sidebar.selectbox("Status", status_options)
selected_years = st.sidebar.multiselect("Filing Year", year_options)
selected_patent_type = st.sidebar.selectbox("Patent Type", patent_type_options)

filtered = filter_by_company(df, selected_companies)
if selected_country != "All" and "country_name" in filtered.columns:
    filtered = filtered[filtered["country_name"].fillna("Unknown").astype(str).str.strip().replace("", "Unknown") == selected_country]
if selected_status != "All" and "status" in filtered.columns:
    filtered = filtered[filtered["status"] == selected_status]
if selected_years and "filing_year" in filtered.columns:
    filtered = filtered[filtered["filing_year"].isin(selected_years)]
if selected_patent_type != "All" and "patent_type" in filtered.columns:
    filtered = filtered[filtered["patent_type"] == selected_patent_type]

if filtered.empty:
    st.warning("No patents found for the selected technology filters.")
    st.stop()

cpc_df = explode_cpc_sections(filtered)
if cpc_df.empty:
    st.warning("No CPC section data available in the current dataset.")
    st.stop()

st.subheader("Top Technology Buckets")
bucket_counts = cpc_df["cpc_display"].value_counts().head(15).reset_index()
bucket_counts.columns = ["cpc_display", "count"]
fig = px.bar(bucket_counts.sort_values("count", ascending=True), x="count", y="cpc_display", orientation="h")
st.plotly_chart(fig, use_container_width=True)
st.info(summarize_cpc_signal(cpc_df))

st.subheader("Technology Trends Over Time")
trend_df = cpc_df.dropna(subset=["filing_year"]).copy()
if not trend_df.empty:
    trend_df["filing_year"] = trend_df["filing_year"].astype(int)
    top_sections = cpc_df["cpc_display"].value_counts().head(5).index.tolist()
    trend_counts = trend_df[trend_df["cpc_display"].isin(top_sections)].groupby(["filing_year", "cpc_display"]).size().reset_index(name="count")
    fig = px.line(trend_counts, x="filing_year", y="count", color="cpc_display", markers=True)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No filing-year data available for the technology trends chart.")

st.subheader("Company vs Technology Bucket Heatmap")
top_companies = clean_named_series(cpc_df["company"], fallback="Unassigned").value_counts().head(10).index.tolist()
top_sections = cpc_df["cpc_display"].value_counts().head(10).index.tolist()
heat_company = cpc_df[cpc_df["company"].fillna("Unassigned").astype(str).str.strip().replace("", "Unassigned").isin(top_companies) & cpc_df["cpc_display"].isin(top_sections)].copy()
heat_company["company"] = heat_company["company"].fillna("Unassigned").astype(str).str.strip().replace("", "Unassigned")
company_heat = heat_company.groupby(["company", "cpc_display"]).size().reset_index(name="count")
fig = px.density_heatmap(company_heat, x="cpc_display", y="company", z="count", histfunc="sum", labels={"company": "Company", "cpc_display": "Technology Bucket", "count": "Patent Count"})
st.plotly_chart(fig, use_container_width=True)

st.subheader("Country vs Technology Bucket Heatmap")
country_series = clean_named_series(cpc_df["country_name"], fallback="Unknown")
country_series = country_series[country_series.str.lower() != "unknown"]
top_countries = country_series.value_counts().head(10).index.tolist()
if top_countries:
    heat_country = cpc_df[cpc_df["cpc_display"].isin(top_sections)].copy()
    heat_country["country_name"] = heat_country["country_name"].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
    heat_country = heat_country[heat_country["country_name"].isin(top_countries)]
    country_heat = heat_country.groupby(["country_name", "cpc_display"]).size().reset_index(name="count")
    fig = px.density_heatmap(country_heat, x="cpc_display", y="country_name", z="count", histfunc="sum", labels={"country_name": "Country / Jurisdiction", "cpc_display": "Technology Bucket", "count": "Patent Count"})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Country visibility is limited in the current view, so no clean country heatmap is shown.")

st.subheader("Technology Bucket Drilldown")
bucket_options = sorted(cpc_df["cpc_display"].dropna().astype(str).unique().tolist())
selected_bucket = st.selectbox("Select a technology bucket", bucket_options)

selected_ids = cpc_df[cpc_df["cpc_display"] == selected_bucket]["patent_id"].dropna().astype(str).unique().tolist()
bucket_patents = filtered[filtered["patent_id"].astype(str).isin(selected_ids)].copy().drop_duplicates(subset=["patent_id"])
st.caption(f"Visible patents mapped to **{selected_bucket}** in the current filter view.")
st.metric("Patent Count", len(bucket_patents))
    
clickable_patent_table(
    bucket_patents,
    title="Technology Bucket Patents",
    key_prefix="technology_landscape_bucket",
    show_cols=["patent_id", "title", "company", "assignee", "inventor", "country_name", "filing_year", "patent_type", "status", "top_level_tech"],
    height=420,
)
