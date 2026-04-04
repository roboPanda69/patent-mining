import streamlit as st
import plotly.express as px
from utils.loader import load_patents
from utils.cpc_utils import explode_cpc_sections
from utils.company_utils import get_company_options

st.title("Compare Views")
st.caption("Compare two portfolio slices side by side for strategy and communication.")

df = load_patents().copy()


def apply_filters(data, company="All", country="All", status="All", years=None, assignee="All"):
    out = data.copy()
    if company != "All" and "company" in out.columns:
        out = out[out["company"] == company]
    if country != "All" and "country_name" in out.columns:
        out = out[out["country_name"] == country]
    if status != "All" and "status" in out.columns:
        out = out[out["status"] == status]
    if years and "filing_year" in out.columns:
        out = out[out["filing_year"].isin(years)]
    if assignee != "All" and "assignee" in out.columns:
        out = out[out["assignee"] == assignee]
    return out


def apply_bucket_filter(data, bucket="All"):
    if bucket == "All" or "cpc_sections" not in data.columns:
        return data.copy()
    cpc_df = explode_cpc_sections(data)
    if cpc_df.empty:
        return data.head(0).copy()
    ids = cpc_df[cpc_df["cpc_display"] == bucket]["patent_id"].dropna().astype(str).unique().tolist()
    return data[data["patent_id"].astype(str).isin(ids)].copy()


def metric_block(data):
    return {
        "Total Patents": len(data),
        "Granted": int((data["status"] == "Granted").sum()) if "status" in data.columns else 0,
        "Published Applications": int((data["status"] == "Published Application").sum()) if "status" in data.columns else 0,
        "Countries": int(data["country_name"].nunique()) if "country_name" in data.columns else 0,
        "Companies": int(data["company"].nunique()) if "company" in data.columns else 0,
    }


def render_patent_open_selector(data, label_prefix: str):
    if data.empty or "patent_id" not in data.columns:
        return
    options = data[["patent_id", "title"]].dropna(subset=["patent_id"]).drop_duplicates().copy()
    if options.empty:
        return
    options["display"] = options.apply(lambda r: f"{r['patent_id']} — {r.get('title', '')}", axis=1)
    display_options = ["Select a patent"] + options["display"].tolist()
    selected = st.selectbox("Open patent detail", display_options, key=f"open_detail_{label_prefix}")
    if selected != "Select a patent":
        patent_id = selected.split(" — ", 1)[0]
        if st.button("Open Patent Detail", key=f"open_btn_{label_prefix}"):
            st.session_state["selected_patent_id"] = patent_id
            st.switch_page("pages/patent_detail.py")


company_options = get_company_options(df, include_all=True)
country_options = ["All"] + sorted(df["country_name"].dropna().astype(str).unique().tolist())
status_options = ["All"] + sorted(df["status"].dropna().astype(str).unique().tolist())
year_options = sorted(df["filing_year"].dropna().astype(int).unique().tolist())
assignee_options = ["All"] + sorted(df["assignee"].dropna().astype(str).unique().tolist())
bucket_options = ["All"]
if "cpc_sections" in df.columns:
    cpc_df = explode_cpc_sections(df)
    if not cpc_df.empty:
        bucket_options += sorted(cpc_df["cpc_display"].dropna().astype(str).unique().tolist())

left, right = st.columns(2)
with left:
    st.subheader("View A")
    a_company = st.selectbox("Company", company_options, key="a_company")
    a_country = st.selectbox("Country", country_options, key="a_country")
    a_status = st.selectbox("Status", status_options, key="a_status")
    a_years = st.multiselect("Years", year_options, key="a_years")
    a_assignee = st.selectbox("Assignee", assignee_options, key="a_assignee")
    a_bucket = st.selectbox("Technology Bucket", bucket_options, key="a_bucket")
with right:
    st.subheader("View B")
    b_company = st.selectbox("Company", company_options, key="b_company")
    b_country = st.selectbox("Country", country_options, key="b_country")
    b_status = st.selectbox("Status", status_options, key="b_status")
    b_years = st.multiselect("Years", year_options, key="b_years")
    b_assignee = st.selectbox("Assignee", assignee_options, key="b_assignee")
    b_bucket = st.selectbox("Technology Bucket", bucket_options, key="b_bucket")

view_a = apply_bucket_filter(apply_filters(df, a_company, a_country, a_status, a_years, a_assignee), a_bucket)
view_b = apply_bucket_filter(apply_filters(df, b_company, b_country, b_status, b_years, b_assignee), b_bucket)

left, right = st.columns(2)
for container, title, data in [(left, "View A Metrics", view_a), (right, "View B Metrics", view_b)]:
    with container:
        st.markdown("### %s" % title)
        metrics = metric_block(data)
        cols = st.columns(len(metrics))
        for idx, (label, value) in enumerate(metrics.items()):
            cols[idx].metric(label, value)

left, right = st.columns(2)
for container, title, data, chart_key in [
    (left, "View A Filing Trend", view_a, "view_a_filing_trend"),
    (right, "View B Filing Trend", view_b, "view_b_filing_trend"),
]:
    with container:
        st.markdown("### %s" % title)
        if data.empty or data["filing_year"].dropna().empty:
            st.info("No filing-year data available.")
        else:
            counts = data["filing_year"].dropna().astype(int).value_counts().sort_index().reset_index()
            counts.columns = ["filing_year", "count"]
            fig = px.line(counts, x="filing_year", y="count", markers=True)
            st.plotly_chart(fig, use_container_width=True, key=chart_key)

left, right = st.columns(2)
for container, title, data, chart_key in [
    (left, "View A Technology Split", view_a, "view_a_tech_split"),
    (right, "View B Technology Split", view_b, "view_b_tech_split"),
]:
    with container:
        st.markdown("### %s" % title)
        if "top_level_tech" not in data.columns or data.empty:
            st.info("No technology data available.")
        else:
            tech = data["top_level_tech"].fillna("Other / Unmapped").value_counts().head(10).reset_index()
            tech.columns = ["top_level_tech", "count"]
            fig = px.bar(tech.sort_values("count", ascending=True), x="count", y="top_level_tech", orientation="h")
            st.plotly_chart(fig, use_container_width=True, key=chart_key)

left, right = st.columns(2)
with left:
    st.subheader("View A Sample")
    show_cols = [c for c in ["patent_id", "title", "company", "assignee", "country_name", "filing_year", "status"] if c in view_a.columns]
    st.dataframe(view_a[show_cols].head(20), use_container_width=True, height=320)
    render_patent_open_selector(view_a.head(20), "compare_a")
with right:
    st.subheader("View B Sample")
    show_cols = [c for c in ["patent_id", "title", "company", "assignee", "country_name", "filing_year", "status"] if c in view_b.columns]
    st.dataframe(view_b[show_cols].head(20), use_container_width=True, height=320)
    render_patent_open_selector(view_b.head(20), "compare_b")
