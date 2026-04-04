import pandas as pd
import plotly.express as px
import streamlit as st

from utils.trl_loader import load_trl_normalized, load_trl_topic_metrics
from utils.trl_utils import ordered_topics

st.title("Technology Maturity Radar")
st.caption("A topic-level research-to-patent view that helps leadership understand where technologies appear research-led, translating, or commercializing.")

normalized = load_trl_normalized()
metrics = load_trl_topic_metrics()

if normalized.empty or metrics.empty:
    st.warning(
        "No TRL datasets are available yet. Add the TRL paper and TRL patent files, run the TRL preprocess scripts, and then reopen this page."
    )
    st.stop()

# ---------------------------------------------------
# Sidebar filters
# ---------------------------------------------------
st.sidebar.header("Radar Filters")

topic_options = ordered_topics(metrics["topic_name"].dropna().astype(str).unique().tolist())
selected_topics = st.sidebar.multiselect("Topic", topic_options, default=topic_options)
selected_sources = st.sidebar.multiselect("Source", ["paper", "patent"], default=["paper", "patent"])

topic_filtered_metrics = metrics[metrics["topic_name"].isin(selected_topics)].copy() if selected_topics else metrics.copy()
normalized_filtered = normalized[
    normalized["topic_name"].isin(selected_topics) &
    normalized["source_type"].isin(selected_sources)
].copy() if selected_topics else normalized[normalized["source_type"].isin(selected_sources)].copy()

if topic_filtered_metrics.empty or normalized_filtered.empty:
    st.warning("No TRL records remain after the selected filters.")
    st.stop()

# ---------------------------------------------------
# Overview cards
# ---------------------------------------------------
st.subheader("Topic Overview")

card_topics = topic_filtered_metrics.to_dict("records")
for start in range(0, len(card_topics), 3):
    cols = st.columns(3)
    for col, record in zip(cols, card_topics[start:start + 3]):
        with col:
            with st.container(border=True):
                st.markdown(f"### {record['topic_name']}")
                c1, c2 = st.columns(2)
                c1.metric("Papers", int(record["paper_count"]))
                c2.metric("Patents", int(record["patent_count"]))
                st.markdown(f"**Top institution:** {record['top_institution']}")
                st.markdown(f"**Top company:** {record['top_company']}")
                st.markdown(f"**Maturity band:** {record['maturity_band']}")
                st.info(record["maturity_reason"])

st.divider()

# ---------------------------------------------------
# Research vs patent matrix
# ---------------------------------------------------
st.subheader("Research vs Patent Matrix")
st.caption("Topics in the upper-right are both research-active and patent-active. Topics with strong research but lighter patenting can indicate emerging opportunity or an earlier maturity stage.")

fig = px.scatter(
    topic_filtered_metrics,
    x="research_intensity",
    y="patent_intensity",
    size="paper_count",
    color="maturity_band",
    hover_name="topic_name",
    text="topic_name",
    labels={
        "research_intensity": "Research Intensity",
        "patent_intensity": "Patent Intensity",
    },
)
fig.update_traces(textposition="top center")
st.plotly_chart(fig, use_container_width=True, key="trl_scatter")

st.divider()

# ---------------------------------------------------
# Topic deep-dive
# ---------------------------------------------------
st.subheader("Topic Deep-Dive")
selected_topic = st.selectbox("Select a topic to inspect", topic_options)

topic_docs = normalized_filtered[normalized_filtered["topic_name"] == selected_topic].copy()
topic_summary = topic_filtered_metrics[topic_filtered_metrics["topic_name"] == selected_topic].iloc[0]

paper_docs = topic_docs[topic_docs["source_type"] == "paper"].copy()
patent_docs = topic_docs[topic_docs["source_type"] == "patent"].copy()

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Paper Count", int(topic_summary["paper_count"]))
m2.metric("Patent Count", int(topic_summary["patent_count"]))
m3.metric("Top Institution", topic_summary["top_institution"])
m4.metric("Top Company", topic_summary["top_company"])
m5.metric("Maturity Band", topic_summary["maturity_band"])

st.info(topic_summary["maturity_reason"])
st.caption(topic_summary["transition_signal"])

left, right = st.columns(2)

with left:
    st.markdown("### Research vs Patent Trend")
    trend = (
        topic_docs.dropna(subset=["year"])
        .groupby(["year", "source_type"])
        .size()
        .reset_index(name="count")
        .sort_values(["year", "source_type"])
    )
    if trend.empty:
        st.info("Not enough year data to show the topic timeline.")
    else:
        fig = px.line(
            trend,
            x="year",
            y="count",
            color="source_type",
            markers=True,
            labels={"year": "Year", "count": "Document Count", "source_type": "Source"},
        )
        st.plotly_chart(fig, use_container_width=True, key="trl_topic_trend")

with right:
    st.markdown("### Strategic Interpretation")
    paper_count = int(topic_summary["paper_count"])
    patent_count = int(topic_summary["patent_count"])
    if paper_count > patent_count * 2:
        st.write("This topic currently looks research-led, with academic activity outpacing patent protection. For leadership, this can indicate an earlier-stage or whitespace area worth monitoring.")
    elif patent_count > paper_count * 1.25:
        st.write("This topic shows stronger industry conversion, with patenting intensity now more visible than research volume. For leadership, that usually signals active competitive positioning.")
    else:
        st.write("This topic sits in a more balanced zone, where research visibility and patent protection are both present. For leadership, that often suggests an active transition from science into product and IP strategy.")

    st.write(f"The current visible topic keywords are: **{topic_summary['topic_keywords'] or 'No clear keyword cluster yet'}**.")
    st.write("Why this matters to JLR: this view helps separate topics that still need research watching from those where competitive IP intensity may already justify stronger strategic action.")

low_left, low_right = st.columns(2)

with low_left:
    st.markdown("### Leading Institutions")
    if paper_docs.empty:
        st.info("No paper records are available for this topic.")
    else:
        inst_counts = paper_docs["organization_name"].fillna("Unknown").value_counts().head(12).reset_index()
        inst_counts.columns = ["organization_name", "count"]
        fig = px.bar(
            inst_counts.sort_values("count", ascending=True),
            x="count",
            y="organization_name",
            orientation="h",
            labels={"count": "Paper Count", "organization_name": "Institution"},
        )
        st.plotly_chart(fig, use_container_width=True, key="trl_institutions")

with low_right:
    st.markdown("### Leading Companies / Assignees")
    if patent_docs.empty:
        st.info("No patent records are available for this topic.")
    else:
        company_counts = patent_docs["organization_name"].fillna("Unknown").value_counts().head(12).reset_index()
        company_counts.columns = ["organization_name", "count"]
        fig = px.bar(
            company_counts.sort_values("count", ascending=True),
            x="count",
            y="organization_name",
            orientation="h",
            labels={"count": "Patent Count", "organization_name": "Company / Assignee"},
        )
        st.plotly_chart(fig, use_container_width=True, key="trl_companies")

st.divider()

# ---------------------------------------------------
# Opportunity / whitespace hint
# ---------------------------------------------------
st.subheader("Opportunity Radar")
opportunities = topic_filtered_metrics.copy()
opportunities["paper_to_patent_gap"] = opportunities["paper_count"] - opportunities["patent_count"]
opportunities = opportunities.sort_values(["paper_to_patent_gap", "paper_count"], ascending=[False, False])

st.caption("This is not a claim of whitespace certainty. It is a directional signal showing where visible research is stronger than visible patenting in the current public dataset.")

show_cols = [
    "topic_name", "paper_count", "patent_count", "paper_to_patent_gap",
    "top_institution", "top_company", "maturity_band",
]
st.dataframe(opportunities[show_cols], use_container_width=True)

st.divider()

# ---------------------------------------------------
# Source tables
# ---------------------------------------------------
st.subheader("Supporting Records")
tab1, tab2 = st.tabs(["Papers", "Patents"])

with tab1:
    show_cols = ["document_id", "title", "organization_name", "country", "year", "citation_count", "source_link"]
    available_cols = [c for c in show_cols if c in paper_docs.columns]
    st.dataframe(paper_docs[available_cols].sort_values(["year", "citation_count"], ascending=[False, False]), use_container_width=True, height=380)

with tab2:
    show_cols = ["document_id", "title", "organization_name", "country", "year", "patent_status", "source_link"]
    available_cols = [c for c in show_cols if c in patent_docs.columns]
    patent_table = patent_docs[available_cols].sort_values("year", ascending=False)
    st.dataframe(patent_table, use_container_width=True, height=380)

    patent_options = patent_docs["document_id"].dropna().astype(str).tolist()
    if patent_options:
        selected_patent = st.selectbox("Open a patent from this topic", patent_options, key="trl_patent_open_select")
        if st.button("Open Patent Detail", key="trl_patent_open_button"):
            st.session_state["selected_patent_id"] = selected_patent
            st.switch_page("pages/patent_detail.py")
