import streamlit as st
from utils.loader import load_patents
from utils.search_engine import get_search_engine

st.title("Patent Spotlight")
st.caption("A rotating daily spotlight to highlight one notable patent from the portfolio.")

df = load_patents()
engine = get_search_engine(df)

patent = engine.get_daily_spotlight_patent()
if patent is None:
    st.warning("No patents are available.")
    st.stop()

summary = engine.build_spotlight_summary(patent)
st.subheader(patent["title"])

with st.container(border=True):
    st.markdown("**Patent ID:** `%s`" % patent["patent_id"])
    st.markdown("**Company:** %s" % patent.get("company", "Unassigned"))
    st.markdown("**Assignee:** %s" % patent.get("assignee", "Unknown"))
    st.markdown("**Country / Jurisdiction:** %s" % patent.get("country_name", "Unknown"))
    st.markdown("**Technology:** %s" % patent.get("top_level_tech", "Other / Unmapped"))
    if patent.get("result_link"):
        st.markdown("[Open Patent Link](%s)" % patent["result_link"])

st.info(summary["what_it_is"])
st.info(summary["why_it_matters"])
st.info(summary["portfolio_context"])

if st.button("Open details"):
    st.session_state["selected_patent_id"] = patent["patent_id"]
    st.switch_page("pages/patent_detail.py")
