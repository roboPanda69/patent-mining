import streamlit as st
import plotly.express as px

from utils.loader import load_patents
from utils.company_utils import filter_by_company, get_company_options
from utils.ui_helpers import clickable_patent_table, clean_named_series, top_known_value

st.title("Technology Classification")
st.caption("A business-friendly technology theme view built on the mapped patent classification layer.")

df = load_patents().copy()

st.sidebar.header("Technology Theme Filters")
company_options = get_company_options(df, include_all=True)
default_companies = ["JLR"] if "JLR" in company_options else ["All"]
selected_companies = st.sidebar.multiselect("Company", company_options, default=default_companies)
country_options = ["All"] + sorted(clean_named_series(df["country_name"], fallback="Unknown").unique().tolist()) if "country_name" in df.columns else ["All"]
status_options = ["All"] + sorted(df["status"].dropna().astype(str).unique().tolist()) if "status" in df.columns else ["All"]
year_options = sorted(df["filing_year"].dropna().astype(int).unique().tolist()) if "filing_year" in df.columns else []

selected_country = st.sidebar.selectbox("Country / Jurisdiction", country_options)
selected_status = st.sidebar.selectbox("Status", status_options)
selected_years = st.sidebar.multiselect("Filing Year", year_options)

filtered = filter_by_company(df, selected_companies)
if selected_country != "All" and "country_name" in filtered.columns:
    filtered = filtered[filtered["country_name"].fillna("Unknown").astype(str).str.strip().replace("", "Unknown") == selected_country]
if selected_status != "All" and "status" in filtered.columns:
    filtered = filtered[filtered["status"] == selected_status]
if selected_years and "filing_year" in filtered.columns:
    filtered = filtered[filtered["filing_year"].isin(selected_years)]

if filtered.empty:
    st.warning("No patents found for the selected technology theme filters.")
    st.stop()

filtered["top_level_tech"] = filtered["top_level_tech"].fillna("Other / Unmapped").astype(str).str.strip().replace("", "Other / Unmapped")
filtered["sub_tech"] = filtered["sub_tech"].fillna("").astype(str).str.strip()

st.subheader("Technology Theme Overview")
tech_counts = filtered["top_level_tech"].value_counts().reset_index()
tech_counts.columns = ["top_level_tech", "count"]
fig = px.bar(tech_counts.sort_values("count", ascending=True).tail(12), x="count", y="top_level_tech", orientation="h")
st.plotly_chart(fig, use_container_width=True)

top_theme, top_theme_count = top_known_value(filtered["top_level_tech"], fallback="Other / Unmapped")
focus_share = top_theme_count / max(len(filtered), 1)
if top_theme == "Other / Unmapped":
    st.info("The visible portfolio is spread across multiple mapped themes, with a meaningful share still sitting outside the named business-friendly technology buckets.")
elif focus_share >= 0.35:
    st.info(f"The clearest mapped technology signal in the current view is **{top_theme}**, accounting for roughly **{focus_share:.0%}** of the visible patent set.")
else:
    st.info(f"The current view is diversified across several mapped technology themes, with **{top_theme}** emerging as the leading directional signal.")

st.subheader("Technology Theme Trends Over Time")
trend_df = filtered.dropna(subset=["filing_year"]).copy()
if not trend_df.empty:
    trend_df["filing_year"] = trend_df["filing_year"].astype(int)
    top_themes = trend_df["top_level_tech"].value_counts().head(5).index.tolist()
    trend_counts = trend_df[trend_df["top_level_tech"].isin(top_themes)].groupby(["filing_year", "top_level_tech"]).size().reset_index(name="count")
    fig = px.line(trend_counts, x="filing_year", y="count", color="top_level_tech", markers=True)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No filing-year data is available for the technology trend chart.")

left, right = st.columns(2)
with left:
    st.subheader("Company vs Theme")
    heat = filtered.copy()
    heat["company"] = heat["company"].fillna("Unassigned").astype(str).str.strip().replace("", "Unassigned")
    top_companies = clean_named_series(heat["company"], fallback="Unassigned").value_counts().head(10).index.tolist()
    top_themes = heat["top_level_tech"].value_counts().head(8).index.tolist()
    heat = heat[heat["company"].isin(top_companies) & heat["top_level_tech"].isin(top_themes)]
    if not heat.empty:
        company_heat = heat.groupby(["company", "top_level_tech"]).size().reset_index(name="count")
        fig = px.density_heatmap(company_heat, x="top_level_tech", y="company", z="count", histfunc="sum")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Company-theme intersections are limited in the current view.")
with right:
    st.subheader("Country vs Theme")
    heat = filtered.copy()
    heat["country_name"] = heat["country_name"].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
    known_countries = heat[heat["country_name"].str.lower() != "unknown"]
    top_countries = known_countries["country_name"].value_counts().head(10).index.tolist()
    top_themes = heat["top_level_tech"].value_counts().head(8).index.tolist()
    heat = heat[heat["country_name"].isin(top_countries) & heat["top_level_tech"].isin(top_themes)]
    if not heat.empty:
        country_heat = heat.groupby(["country_name", "top_level_tech"]).size().reset_index(name="count")
        fig = px.density_heatmap(country_heat, x="top_level_tech", y="country_name", z="count", histfunc="sum")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Country-theme intersections are limited in the current view.")

st.subheader("Theme Drilldown")
theme_options = sorted(filtered["top_level_tech"].dropna().astype(str).unique().tolist())
selected_theme = st.selectbox("Select a mapped technology theme", theme_options)
theme_patents = filtered[filtered["top_level_tech"] == selected_theme].copy().drop_duplicates(subset=["patent_id"])

sub_tech_signal = theme_patents[theme_patents["sub_tech"] != ""]["sub_tech"] if "sub_tech" in theme_patents.columns else []
if len(sub_tech_signal) > 0:
    sub_label, sub_count = top_known_value(theme_patents[theme_patents["sub_tech"] != ""]["sub_tech"], fallback="Not clearly identified")
    st.caption(f"Within **{selected_theme}**, the strongest visible sub-theme is **{sub_label}** ({sub_count} patents).")

clickable_patent_table(
    theme_patents,
    title="Theme Patent Table",
    key_prefix="technology_classification_theme",
    show_cols=["patent_id", "title", "company", "assignee", "country_name", "filing_year", "status", "top_level_tech", "sub_tech"],
    height=420,
)
