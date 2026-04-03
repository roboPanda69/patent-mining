import streamlit as st
import plotly.express as px
from utils.loader import load_patents
from utils.company_utils import get_company_options, filter_by_company
from utils.cpc_utils import explode_cpc_sections

st.title("Technology Landscape")
st.caption("Analyze patents by CPC technology buckets and company context.")

df = load_patents().copy()
st.sidebar.header("Technology Filters")
company_options = get_company_options(df, include_all=True)
selected_companies = st.sidebar.multiselect("Company", company_options, default=["All"])
df = filter_by_company(df, selected_companies)

if df.empty:
    st.warning("No patents found for the selected company filter.")
    st.stop()

cpc_df = explode_cpc_sections(df)
if cpc_df.empty:
    st.warning("No CPC section data available in the current dataset.")
    st.stop()

st.subheader("Top Technology Buckets")
bucket_counts = cpc_df["cpc_display"].value_counts().head(15).reset_index()
bucket_counts.columns = ["cpc_display", "count"]
fig = px.bar(bucket_counts.sort_values("count", ascending=True), x="count", y="cpc_display", orientation="h")
st.plotly_chart(fig, use_container_width=True)

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
top_companies = cpc_df["company"].fillna("Unassigned").value_counts().head(10).index.tolist()
top_sections = cpc_df["cpc_display"].value_counts().head(10).index.tolist()
heat_company = cpc_df[cpc_df["company"].fillna("Unassigned").isin(top_companies) & cpc_df["cpc_display"].isin(top_sections)].copy()
company_heat = heat_company.groupby(["company", "cpc_display"]).size().reset_index(name="count")
fig = px.density_heatmap(company_heat, x="cpc_display", y="company", z="count", histfunc="sum", labels={"company": "Company", "cpc_display": "Technology Bucket", "count": "Patent Count"})
st.plotly_chart(fig, use_container_width=True)

st.subheader("Country vs Technology Bucket Heatmap")
top_countries = cpc_df["country_name"].fillna("Unknown").value_counts().head(10).index.tolist()
heat_country = cpc_df[cpc_df["country_name"].fillna("Unknown").isin(top_countries) & cpc_df["cpc_display"].isin(top_sections)].copy()
country_heat = heat_country.groupby(["country_name", "cpc_display"]).size().reset_index(name="count")
fig = px.density_heatmap(country_heat, x="cpc_display", y="country_name", z="count", histfunc="sum", labels={"country_name": "Country / Jurisdiction", "cpc_display": "Technology Bucket", "count": "Patent Count"})
st.plotly_chart(fig, use_container_width=True)

st.subheader("Technology Bucket Drilldown")
bucket_options = sorted(cpc_df["cpc_display"].dropna().astype(str).unique().tolist())
selected_bucket = st.selectbox("Select a technology bucket", bucket_options)

selected_ids = cpc_df[cpc_df["cpc_display"] == selected_bucket]["patent_id"].dropna().astype(str).unique().tolist()
bucket_patents = df[df["patent_id"].astype(str).isin(selected_ids)].copy().drop_duplicates(subset=["patent_id"])

show_cols = ["patent_id", "title", "company", "assignee", "inventor", "country_name", "filing_year", "patent_type", "status", "top_level_tech"]
show_cols = [c for c in show_cols if c in bucket_patents.columns]
st.dataframe(bucket_patents[show_cols], use_container_width=True, height=420)

st.markdown("Open a patent from Search or copy the patent ID into Search Patents to view details.")
