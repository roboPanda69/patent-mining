import streamlit as st
import pandas as pd
from utils.loader import load_patents
from utils.search_engine import get_search_engine
from utils.cpc_utils import parse_list_like, section_label
from utils.company_utils import format_date_ddmmyyyy

st.title("Patent Detail")

df = load_patents()
engine = get_search_engine(df)
selected_patent_id = st.session_state.get("selected_patent_id", None)

top_col1, top_col2 = st.columns([1, 5])
with top_col1:
    if st.button("← Back to Search", use_container_width=True):
        st.switch_page("pages/search.py")

if not selected_patent_id:
    st.info("No patent selected yet. Go to the Search page and click 'View Details' on a result.")
    st.stop()

patent = engine.get_patent_by_id(selected_patent_id)
if patent is None:
    st.error("Selected patent could not be found.")
    st.stop()

st.subheader(patent["title"])
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Patent ID:** `%s`" % patent["patent_id"])
        st.markdown("**Company:** %s" % (patent.get("company", "Unassigned")))
        st.markdown("**Assignee:** %s" % (patent["assignee"] if patent["assignee"] else "Unknown"))
        st.markdown("**Inventor:** %s" % (patent["inventor"] if patent["inventor"] else "Unknown"))
        st.markdown("**Country / Jurisdiction:** %s" % (patent["country_name"] if patent["country_name"] else "Unknown"))
    with col2:
        st.markdown("**Status:** %s" % (patent["status"] if patent["status"] else "Unknown"))
        st.markdown("**Priority Date:** %s" % (format_date_ddmmyyyy(patent.get("priority_date")) or "Unknown"))
        st.markdown("**Filing Date:** %s" % (format_date_ddmmyyyy(patent.get("filing_date")) or "Unknown"))
        st.markdown("**Publication Date:** %s" % (format_date_ddmmyyyy(patent.get("publication_date")) or "Unknown"))
        st.markdown("**Grant Date:** %s" % (format_date_ddmmyyyy(patent.get("grant_date")) or "Unknown"))

    if pd.notna(patent.get("result_link")) and str(patent.get("result_link")).strip():
        st.markdown("[Open Patent Link](%s)" % patent["result_link"])

if "abstract" in patent and pd.notna(patent["abstract"]) and str(patent["abstract"]).strip():
    st.divider()
    st.subheader("Abstract")
    st.write(patent["abstract"])

col_a, col_b = st.columns(2)
with col_a:
    if "cpc_codes" in patent and pd.notna(patent["cpc_codes"]) and str(patent["cpc_codes"]).strip():
        st.subheader("CPC Codes")
        st.write(patent["cpc_codes"])
with col_b:
    if "patent_type" in patent and pd.notna(patent["patent_type"]) and str(patent["patent_type"]).strip():
        st.subheader("Patent Type")
        st.write(patent["patent_type"])

st.markdown("**Top-level Technology:** %s" % (patent.get("top_level_tech", "Other / Unmapped") or "Other / Unmapped"))
if patent.get("sub_tech"):
    st.markdown("**Sub-technology:** %s" % patent.get("sub_tech"))

if "cpc_sections" in patent and pd.notna(patent["cpc_sections"]) and str(patent["cpc_sections"]).strip():
    raw_sections = parse_list_like(patent["cpc_sections"])
    if raw_sections:
        st.subheader("Technology Buckets")
        for sec in raw_sections:
            st.markdown("- **%s** — %s" % (sec, section_label(sec)))

st.divider()

same_company = engine.get_related_patents(selected_patent_id, top_k=6, company_mode="same_company")
other_companies = engine.get_related_patents(selected_patent_id, top_k=6, company_mode="other_companies")
same_country = engine.get_same_country_patents(selected_patent_id, top_k=6)

tab1, tab2, tab3 = st.tabs(["Similar Patents from Same Company", "Similar Patents from Other Companies", "Same Country"])

def render_patent_list(data: pd.DataFrame, empty_message: str, section_key: str):
    if data.empty:
        st.info(empty_message)
        return
    for i, (_, row) in enumerate(data.iterrows(), start=1):
        with st.container(border=True):
            st.markdown("### %s. %s" % (i, row["title"]))
            st.markdown("**Patent ID:** `%s`" % row["patent_id"])
            st.markdown("**Company:** %s" % (row["company"] if row["company"] else "Unassigned"))
            st.markdown("**Assignee:** %s" % (row["assignee"] if row["assignee"] else "Unknown"))
            st.markdown("**Country / Jurisdiction:** %s" % (row["country_name"] if row["country_name"] else "Unknown"))
            if "related_score" in row:
                st.markdown("**Similarity Score:** %.3f" % row["related_score"])
            if "relevance_reason" in row:
                st.info("Why relevant: %s" % row["relevance_reason"])
            c1, c2 = st.columns(2)
            with c1:
                if pd.notna(row.get("result_link")) and str(row.get("result_link")).strip():
                    st.markdown("[Open Patent Link](%s)" % row["result_link"])
            with c2:
                button_key = "open_%s_%s_%s" % (section_key, i, row["patent_id"])
                if st.button("Open This Patent", key=button_key):
                    st.session_state["selected_patent_id"] = row["patent_id"]
                    st.rerun()

with tab1:
    render_patent_list(same_company, "No same-company similar patents found.", "same_company")
with tab2:
    render_patent_list(other_companies, "No competitor similar patents found.", "other_company")
with tab3:
    render_patent_list(same_country, "No same-country patents found.", "country")
