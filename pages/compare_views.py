import plotly.express as px
import streamlit as st

from utils.loader import load_patents
from utils.cpc_utils import explode_cpc_sections
from utils.ui_helpers import clickable_patent_table, clean_named_series

st.title("Compare Views")
st.caption("Compare two portfolio slices side-by-side.")

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


def apply_bucket_filter(data, bucket):
    if bucket == "All" or "cpc_sections" not in data.columns:
        return data.copy()
    cpc_df = explode_cpc_sections(data)
    if cpc_df.empty:
        return data.head(0).copy()
    matched_ids = cpc_df[cpc_df["cpc_display"] == bucket]["patent_id"].dropna().astype(str).unique().tolist()
    return data[data["patent_id"].astype(str).isin(matched_ids)].copy()


def metric_block(data):
    total = len(data)
    granted = int(data["is_granted"].sum()) if "is_granted" in data.columns else 0
    published = int(data["is_published"].sum()) if "is_published" in data.columns else 0
    countries = int(clean_named_series(data["country_name"]).nunique()) if "country_name" in data.columns else 0
    assignees = int(clean_named_series(data["assignee"]).nunique()) if "assignee" in data.columns else 0
    return total, granted, published, countries, assignees


def top_label(series):
    counts = clean_named_series(series).value_counts()
    if counts.empty:
        return "N/A", 0
    return counts.index[0], int(counts.iloc[0])


def narrative(name, data):
    if data.empty:
        return f"**{name}:** No patents in this filtered view."
    total, granted, published, countries, assignees = metric_block(data)
    country_name, country_count = top_label(data["country_name"]) if "country_name" in data.columns else ("N/A", 0)
    assignee_name, assignee_count = top_label(data["assignee"]) if "assignee" in data.columns else ("N/A", 0)
    status_name, status_count = top_label(data["status"]) if "status" in data.columns else ("N/A", 0)
    return (
        f"**{name}:** {total} patents. Leading jurisdiction: **{country_name}** ({country_count}). "
        f"Leading assignee: **{assignee_name}** ({assignee_count}). Dominant status: **{status_name}** ({status_count})."
    )


def year_chart(data, title, key):
    st.subheader(title)
    if data.empty or "filing_year" not in data.columns or not data["filing_year"].notna().any():
        st.info("No filing-year data available.")
        return
    year_counts = data["filing_year"].dropna().astype(int).value_counts().sort_index().reset_index()
    year_counts.columns = ["filing_year", "count"]
    fig = px.line(year_counts, x="filing_year", y="count", markers=True)
    st.plotly_chart(fig, use_container_width=True, key=key)


def bucket_chart(data, title, key):
    st.subheader(title)
    if data.empty or "cpc_sections" not in data.columns:
        st.info("No CPC data available.")
        return
    cpc_df = explode_cpc_sections(data)
    if cpc_df.empty:
        st.info("No CPC data available.")
        return
    bucket_counts = cpc_df["cpc_display"].value_counts().head(10).sort_values(ascending=True).reset_index()
    bucket_counts.columns = ["cpc_display", "count"]
    fig = px.bar(bucket_counts, x="count", y="cpc_display", orientation="h")
    st.plotly_chart(fig, use_container_width=True, key=key)


company_options = ["All"] + sorted(df["company"].dropna().astype(str).unique().tolist()) if "company" in df.columns else ["All"]
country_options = ["All"] + sorted(df["country_name"].dropna().astype(str).unique().tolist()) if "country_name" in df.columns else ["All"]
status_options = ["All"] + sorted(df["status"].dropna().astype(str).unique().tolist()) if "status" in df.columns else ["All"]
year_options = sorted(df["filing_year"].dropna().astype(int).unique().tolist()) if "filing_year" in df.columns else []
assignee_options = ["All"] + sorted(df["assignee"].dropna().astype(str).unique().tolist()) if "assignee" in df.columns else ["All"]

bucket_options = ["All"]
if "cpc_sections" in df.columns:
    cpc_df_all = explode_cpc_sections(df)
    if not cpc_df_all.empty:
        bucket_options += sorted(cpc_df_all["cpc_display"].dropna().astype(str).unique().tolist())

left_cfg, right_cfg = st.columns(2)
with left_cfg:
    st.subheader("View A")
    a_label = st.text_input("Label for View A", value="View A")
    a_company = st.selectbox("Company", company_options, key="a_company")
    a_country = st.selectbox("Country / Jurisdiction", country_options, key="a_country")
    a_status = st.selectbox("Status", status_options, key="a_status")
    a_years = st.multiselect("Filing Year", year_options, key="a_years")
    a_assignee = st.selectbox("Assignee", assignee_options, key="a_assignee")
    a_bucket = st.selectbox("Technology Bucket", bucket_options, key="a_bucket")
with right_cfg:
    st.subheader("View B")
    b_label = st.text_input("Label for View B", value="View B")
    b_company = st.selectbox("Company", company_options, key="b_company")
    b_country = st.selectbox("Country / Jurisdiction", country_options, key="b_country")
    b_status = st.selectbox("Status", status_options, key="b_status")
    b_years = st.multiselect("Filing Year", year_options, key="b_years")
    b_assignee = st.selectbox("Assignee", assignee_options, key="b_assignee")
    b_bucket = st.selectbox("Technology Bucket", bucket_options, key="b_bucket")

view_a = apply_bucket_filter(apply_filters(df, a_company, a_country, a_status, a_years, a_assignee), a_bucket)
view_b = apply_bucket_filter(apply_filters(df, b_company, b_country, b_status, b_years, b_assignee), b_bucket)

st.divider()
col_a, col_b = st.columns(2)
with col_a:
    st.markdown(f"## {a_label}")
    total, granted, published, countries, assignees = metric_block(view_a)
    k1, k2, k3 = st.columns(3)
    k1.metric("Patents", total)
    k2.metric("Granted", granted)
    k3.metric("Published Applications", published)
    k4, k5 = st.columns(2)
    k4.metric("Countries", countries)
    k5.metric("Assignees", assignees)
    st.info(narrative(a_label, view_a))
with col_b:
    st.markdown(f"## {b_label}")
    total, granted, published, countries, assignees = metric_block(view_b)
    k1, k2, k3 = st.columns(3)
    k1.metric("Patents", total)
    k2.metric("Granted", granted)
    k3.metric("Published Applications", published)
    k4, k5 = st.columns(2)
    k4.metric("Countries", countries)
    k5.metric("Assignees", assignees)
    st.info(narrative(b_label, view_b))

left_chart, right_chart = st.columns(2)
with left_chart:
    year_chart(view_a, f"{a_label} — Filing Trend", key="compare_view_a_year")
    bucket_chart(view_a, f"{a_label} — Top Technology Buckets", key="compare_view_a_bucket")
with right_chart:
    year_chart(view_b, f"{b_label} — Filing Trend", key="compare_view_b_year")
    bucket_chart(view_b, f"{b_label} — Top Technology Buckets", key="compare_view_b_bucket")

st.divider()
st.subheader("Direct Comparison Summary")
a_patents = len(view_a)
b_patents = len(view_b)
if a_patents > b_patents:
    st.success(f"**{a_label}** has more patents than **{b_label}** by **{a_patents - b_patents}**.")
elif b_patents > a_patents:
    st.success(f"**{b_label}** has more patents than **{a_label}** by **{b_patents - a_patents}**.")
else:
    st.info(f"**{a_label}** and **{b_label}** have the same number of patents.")

left_table, right_table = st.columns(2)
with left_table:
    clickable_patent_table(view_a.head(25), f"{a_label} — Patent Preview", "compare_a")
with right_table:
    clickable_patent_table(view_b.head(25), f"{b_label} — Patent Preview", "compare_b")
