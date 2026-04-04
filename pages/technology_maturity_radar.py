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
from utils.ui_helpers import clickable_patent_table

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

st.sidebar.header("Radar Filters")
selected_topics = st.sidebar.multiselect("Topics", all_topics, default=all_topics)
selected_maturity = st.sidebar.multiselect("Maturity Band", MATURITY_ORDER, default=MATURITY_ORDER)

view_metrics = metrics.copy()
if selected_topics:
    view_metrics = view_metrics[view_metrics["topic_name"].isin(selected_topics)]
if selected_maturity:
    view_metrics = view_metrics[view_metrics["maturity_band"].astype(str).isin(selected_maturity)]

if view_metrics.empty:
    st.warning("No topics available for the selected filters.")
    st.stop()

st.subheader("Maturity Band Progression")
progress_df = pd.DataFrame({
    "Stage": MATURITY_ORDER,
    "Meaning": [
        "Academic and research signals are stronger than patenting signals.",
        "Research is visibly translating into industry and patent activity.",
        "Patenting is accelerating and the topic appears to be moving toward application and deployment.",
        "The topic shows stronger patent depth and a more established industry position.",
    ]
})
st.dataframe(progress_df, use_container_width=True, hide_index=True)

st.subheader("Topic Overview")
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
                st.caption(row["maturity_reason"])
else:
    st.dataframe(
        view_metrics[["topic_name", "paper_count", "patent_count", "top_institution", "top_company", "maturity_band"]],
        use_container_width=True,
        hide_index=True,
    )

st.divider()
st.subheader("Research vs Patent Matrix")
scatter_df = view_metrics.copy()
fig = px.scatter(
    scatter_df,
    x="paper_count",
    y="patent_count",
    size=np.maximum(scatter_df["paper_citations"].fillna(0), 1),
    color="maturity_band",
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

a, b, c = st.columns(3)
a.metric("Papers", int(topic_metric["paper_count"]))
b.metric("Patents", int(topic_metric["patent_count"]))
c.metric("Maturity Band", str(topic_metric["maturity_band"]))
st.info(topic_metric["maturity_reason"])

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
        inst_counts = topic_papers_inst["institution_name"].value_counts().head(12).sort_values(ascending=True).reset_index()
        inst_counts.columns = ["institution_name", "count"]
        fig = px.bar(inst_counts, x="count", y="institution_name", orientation="h")
        st.plotly_chart(fig, use_container_width=True, key="trl_inst_view")
with right:
    st.subheader("Company-Wise Patent View")
    if topic_patents.empty:
        st.info("No patent data is visible for this topic.")
    else:
        company_counts = topic_patents["organization_name"].dropna().astype(str).str.strip()
        company_counts = company_counts[company_counts != ""]
        company_counts = company_counts.value_counts().head(12).sort_values(ascending=True).reset_index()
        company_counts.columns = ["organization_name", "count"]
        fig = px.bar(company_counts, x="count", y="organization_name", orientation="h")
        st.plotly_chart(fig, use_container_width=True, key="trl_company_view")

inst_label, inst_count = best_known_label(topic_papers_inst["institution_name"]) if not topic_papers_inst.empty else ("Not clearly identified", 0)
comp_label, comp_count = best_known_label(topic_patents["organization_name"]) if not topic_patents.empty else ("Not clearly identified", 0)
st.caption(
    f"Top visible institution for this topic is **{inst_label}** ({inst_count} papers), while the strongest visible company patenting presence is **{comp_label}** ({comp_count} patents)."
)

st.subheader("Top Topic Patents")
clickable_patent_table(
    topic_patents.sort_values(by="year", ascending=False) if "year" in topic_patents.columns else topic_patents,
    title="Patent Table",
    key_prefix="trl_topic_patents",
    show_cols=["document_id", "title", "organization_name", "assignee", "country", "year", "status"],
    height=380,
)

# compatibility for patent detail page expecting patent_id
if not topic_patents.empty and "document_id" in topic_patents.columns:
    pass

st.divider()
st.subheader("Institution Lens")
all_institutions = sorted(topic_papers_inst["institution_name"].dropna().astype(str).unique().tolist()) if not topic_papers_inst.empty else []
if all_institutions:
    selected_institution = st.selectbox("Select an institution", all_institutions)
    inst_df = papers_inst[papers_inst["institution_name"] == selected_institution].copy()
    inst_topic_counts = inst_df["topic_name"].value_counts().reset_index()
    inst_topic_counts.columns = ["topic_name", "count"]
    fig = px.bar(inst_topic_counts, x="topic_name", y="count")
    st.plotly_chart(fig, use_container_width=True, key="trl_institution_lens")
    st.info(
        f"{selected_institution} appears in **{len(inst_df)} paper records** across the visible topic set. "
        "This can help identify potential academic talent and collaboration pools by technology domain."
    )
else:
    st.info("No institution-level paper data is available for the Institution Lens yet.")
