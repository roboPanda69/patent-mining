import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.trl_config import MATURITY_ORDER
from utils.trl_loader import (
    load_trl_normalized,
    load_trl_papers,
    load_trl_patents,
    load_trl_papers_by_institution,
    load_trl_topic_metrics,
)
from utils.trl_utils import best_known_label
from utils.ui_helpers import clickable_patent_table, clean_named_series

st.title("Technology Maturity Radar")
st.caption("A topic-level view of how research activity translates into patenting and commercial maturity signals.")

normalized = load_trl_normalized()
papers = load_trl_papers()
patents = load_trl_patents()
papers_inst = load_trl_papers_by_institution()
metrics = load_trl_topic_metrics()

if normalized.empty or metrics.empty:
    st.warning("No TRL dataset is available yet. Run the TRL preprocessing scripts first.")
    st.stop()

all_topics = sorted(metrics["topic_name"].dropna().astype(str).unique().tolist())
trl_stage_options = sorted(metrics["trl_stage_band"].dropna().astype(str).unique().tolist()) if "trl_stage_band" in metrics.columns else []

st.sidebar.header("Radar Filters")
selected_topics = st.sidebar.multiselect("Topics", all_topics, default=all_topics)
selected_maturity = st.sidebar.multiselect("Maturity Band", MATURITY_ORDER, default=MATURITY_ORDER)
selected_trl_bands = st.sidebar.multiselect("TRL-style Stage", trl_stage_options, default=trl_stage_options)

view_metrics = metrics.copy()
if selected_topics:
    view_metrics = view_metrics[view_metrics["topic_name"].isin(selected_topics)]
if selected_maturity:
    view_metrics = view_metrics[view_metrics["maturity_band"].astype(str).isin(selected_maturity)]
if selected_trl_bands and "trl_stage_band" in view_metrics.columns:
    view_metrics = view_metrics[view_metrics["trl_stage_band"].astype(str).isin(selected_trl_bands)]

if view_metrics.empty:
    st.warning("No topics available for the selected filters.")
    st.stop()

st.subheader("TRL-style Progression")
progress_df = pd.DataFrame({
    "TRL-style Stage": ["TRL-like 1-3", "TRL-like 4-6", "TRL-like 7-9"],
    "Meaning": [
        "Research and feasibility signals dominate; patenting remains comparatively limited.",
        "Research and patenting are both visible, indicating technology development and demonstration.",
        "Patent depth and commercialization signals are stronger, pointing toward pilot, launch, and scaled industry activity.",
    ],
})
st.dataframe(progress_df, use_container_width=True, hide_index=True)

st.subheader("Topic Overview")
overview_cols = [
    "topic_name", "paper_count", "patent_count", "top_institution", "top_company", "maturity_band", "trl_stage_band", "trl_stage_score"
]
if len(view_metrics) <= 6:
    cols = st.columns(min(3, max(1, len(view_metrics))))
    for i, (_, row) in enumerate(view_metrics.iterrows()):
        with cols[i % len(cols)]:
            with st.container(border=True):
                st.markdown(f"### {row['topic_name']}")
                st.metric("Papers", int(row["paper_count"]))
                st.metric("Patents", int(row["patent_count"]))
                st.write(f"**Top Institution:** {row['top_institution']}")
                st.write(f"**Top Company:** {row['top_company']}")
                st.success(f"**Maturity Band:** {row['maturity_band']}")
                if "trl_stage_band" in row:
                    st.info(f"**Visible TRL-style Stage:** {row['trl_stage_band']} ({row['trl_stage_name']})")
                st.caption(row["maturity_reason"])
else:
    st.dataframe(view_metrics[[c for c in overview_cols if c in view_metrics.columns]], use_container_width=True, hide_index=True)

st.divider()
st.subheader("Research vs Patent Matrix")
scatter_df = view_metrics.copy()
fig = px.scatter(
    scatter_df,
    x="paper_count",
    y="patent_count",
    size=np.maximum(scatter_df["paper_citations"].fillna(0), 1),
    color="trl_stage_band" if "trl_stage_band" in scatter_df.columns else "maturity_band",
    hover_name="topic_name",
    text="topic_name",
)
fig.update_traces(textposition="top center")
st.plotly_chart(fig, use_container_width=True, key="trl_matrix")

selected_topic = st.selectbox("Topic Deep-Dive", all_topics, index=0)

topic_papers = papers[papers["topic_name"] == selected_topic].copy()
topic_papers_inst = papers_inst[papers_inst["topic_name"] == selected_topic].copy() if not papers_inst.empty else pd.DataFrame()
topic_patents = patents[patents["topic_name"] == selected_topic].copy()
topic_metric = metrics[metrics["topic_name"] == selected_topic].iloc[0]

st.divider()
st.subheader(f"Topic Deep-Dive — {selected_topic}")

a, b, c, d = st.columns(4)
a.metric("Papers", int(topic_metric["paper_count"]))
b.metric("Patents", int(topic_metric["patent_count"]))
c.metric("Maturity Band", str(topic_metric["maturity_band"]))
d.metric("TRL-style Stage", str(topic_metric.get("trl_stage_score", "-")))
st.info(topic_metric["maturity_reason"])
if "trl_stage_reason" in topic_metric:
    st.caption(f"{topic_metric['trl_stage_band']} — {topic_metric['trl_stage_name']}. {topic_metric['trl_stage_reason']}")

trend_rows = []
if not topic_papers.empty and topic_papers["year"].notna().any():
    p_year = topic_papers["year"].dropna().astype(int).value_counts().sort_index()
    trend_rows.extend([{"year": int(y), "count": int(c), "source": "Papers"} for y, c in p_year.items()])
if not topic_patents.empty and topic_patents["year"].notna().any():
    t_year = topic_patents["year"].dropna().astype(int).value_counts().sort_index()
    trend_rows.extend([{"year": int(y), "count": int(c), "source": "Patents"} for y, c in t_year.items()])

if trend_rows:
    trend_df = pd.DataFrame(trend_rows)
    fig = px.line(trend_df, x="year", y="count", color="source", markers=True)
    st.plotly_chart(fig, use_container_width=True, key="trl_topic_trend")

left, right = st.columns(2)
with left:
    st.subheader("Institution-Wise View")
    if topic_papers_inst.empty:
        st.info("No institution-level paper data is visible for this topic.")
    else:
        inst_series = clean_named_series(topic_papers_inst["institution_name"], fallback="Unknown")
        inst_series = inst_series[inst_series.str.lower() != "unknown"]
        if inst_series.empty:
            st.info("No clean institution-level paper signal is visible for this topic.")
        else:
            inst_counts = inst_series.value_counts().head(12).sort_values(ascending=True).reset_index()
            inst_counts.columns = ["institution_name", "count"]
            fig = px.bar(inst_counts, x="count", y="institution_name", orientation="h")
            st.plotly_chart(fig, use_container_width=True, key="trl_inst_view")
with right:
    st.subheader("Company-Wise Patent View")
    if topic_patents.empty:
        st.info("No patent data is visible for this topic.")
    else:
        company_counts = clean_named_series(topic_patents["organization_name"], fallback="Unknown")
        company_counts = company_counts[company_counts.str.lower() != "unknown"]
        if company_counts.empty:
            st.info("No clean company patent signal is visible for this topic.")
        else:
            company_counts = company_counts.value_counts().head(12).sort_values(ascending=True).reset_index()
            company_counts.columns = ["organization_name", "count"]
            fig = px.bar(company_counts, x="count", y="organization_name", orientation="h")
            st.plotly_chart(fig, use_container_width=True, key="trl_company_view")

inst_label, inst_count = best_known_label(topic_papers_inst["institution_name"]) if not topic_papers_inst.empty else ("Not clearly identified", 0)
comp_label, comp_count = best_known_label(topic_patents["organization_name"]) if not topic_patents.empty else ("Not clearly identified", 0)
st.caption(
    f"Top visible institution for this topic is **{inst_label}** ({inst_count} papers), while the strongest visible company patenting presence is **{comp_label}** ({comp_count} patents)."
)

st.divider()
st.subheader("Academic Institution Lens (papers only)")
st.caption("This section looks only at research paper affiliations. It does not combine paper and patent counts together.")
all_institutions = sorted(topic_papers_inst["institution_name"].dropna().astype(str).unique().tolist()) if not topic_papers_inst.empty else []
if all_institutions:
    selected_institution = st.selectbox("Select an academic institution", all_institutions)
    inst_df = papers_inst[papers_inst["institution_name"] == selected_institution].copy()
    inst_topic_counts = inst_df["topic_name"].value_counts().reset_index()
    inst_topic_counts.columns = ["topic_name", "count"]
    fig = px.bar(inst_topic_counts, x="topic_name", y="count")
    st.plotly_chart(fig, use_container_width=True, key="trl_institution_lens")
    st.info(
        f"{selected_institution} appears in **{len(inst_df)} paper records** across the visible topic set. "
        "Use this as a research-affiliation view to spot academic depth and potential university collaboration pools by topic."
    )
else:
    st.info("No institution-level paper data is available for the academic institution lens yet.")

# st.subheader("Patent Organization Lens")
# st.caption("This section looks only at patent organizations / assignees. It does not combine patent and paper counts together.")
# if not patents.empty and "organization_name" in patents.columns:
#     patent_org_series = clean_named_series(patents["organization_name"], fallback="Unknown")
#     all_patent_orgs = sorted(patent_org_series[patent_org_series.str.lower() != "unknown"].unique().tolist())
# else:
#     patent_org_series = pd.Series(dtype="object")
#     all_patent_orgs = []
# if all_patent_orgs:
#     selected_patent_org = st.selectbox("Select a patent organization", all_patent_orgs)
#     org_df = patents[patent_org_series == selected_patent_org].copy()
#     org_topic_counts = org_df["topic_name"].value_counts().reset_index()
#     org_topic_counts.columns = ["topic_name", "count"]
#     fig = px.bar(org_topic_counts, x="topic_name", y="count")
#     st.plotly_chart(fig, use_container_width=True, key="trl_patent_org_lens")
#     latest_year = ""
#     if "year" in org_df.columns and org_df["year"].notna().any():
#         latest_year = f" Latest visible patent year: **{int(org_df['year'].dropna().astype(int).max())}**."
#     st.info(
#         f"{selected_patent_org} appears in **{len(org_df)} patent records** across the visible topic set." + latest_year
#     )
# else:
#     st.info("No clean patent-organization data is available for the patent organization lens yet.")
