import streamlit as st
import pandas as pd
from utils.loader import load_patents
from utils.search_engine import get_search_engine
from utils.company_utils import get_company_options

st.title("Patent Search")
st.caption("Search by patent ID, title, inventor, assignee, company, country, or idea keywords.")

df = load_patents()
engine = get_search_engine(df)

defaults = {
    "search_query": "",
    "search_country": "All",
    "search_status": "All",
    "search_years": [],
    "search_companies": ["All"],
    "search_top_k": 15,
    "search_results": None,
    "search_executed": False,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

st.sidebar.header("Search Filters")
country_options = ["All"] + sorted(df["country_name"].dropna().astype(str).unique().tolist())
status_options = ["All"] + sorted(df["status"].dropna().astype(str).unique().tolist())
year_options = sorted(df["filing_year"].dropna().astype(int).unique().tolist())
company_options = get_company_options(df, include_all=True)

selected_companies = st.sidebar.multiselect("Company", company_options, default=st.session_state["search_companies"])
selected_country = st.sidebar.selectbox("Country / Jurisdiction", country_options, index=country_options.index(st.session_state["search_country"]) if st.session_state["search_country"] in country_options else 0)
selected_status = st.sidebar.selectbox("Status", status_options, index=status_options.index(st.session_state["search_status"]) if st.session_state["search_status"] in status_options else 0)
selected_years = st.sidebar.multiselect("Filing Year", year_options, default=st.session_state["search_years"])
top_k = st.sidebar.slider("Number of results", min_value=5, max_value=50, value=st.session_state["search_top_k"], step=5)

query = st.text_input("Search patents", value=st.session_state["search_query"], placeholder="Examples: GB2612715A, battery thermal management, JLR, BMW, charging control", key="search_query_input")

col_a, col_b = st.columns(2)
with col_a:
    search_clicked = st.button("Search", use_container_width=True)
with col_b:
    clear_clicked = st.button("Clear Search", use_container_width=True)

if clear_clicked:
    for key in ["search_query_input"]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state["search_query"] = ""
    st.session_state["search_country"] = "All"
    st.session_state["search_status"] = "All"
    st.session_state["search_years"] = []
    st.session_state["search_companies"] = ["All"]
    st.session_state["search_top_k"] = 15
    st.session_state["search_results"] = None
    st.session_state["search_executed"] = False
    st.rerun()

if search_clicked:
    st.session_state["search_query"] = query
    st.session_state["search_country"] = selected_country
    st.session_state["search_status"] = selected_status
    st.session_state["search_years"] = selected_years
    st.session_state["search_companies"] = selected_companies if selected_companies else ["All"]
    st.session_state["search_top_k"] = top_k
    st.session_state["search_executed"] = True
    results = engine.search(
        query=query,
        top_k=top_k,
        selected_country=selected_country,
        selected_status=selected_status,
        selected_years=selected_years,
        selected_companies=selected_companies if selected_companies else ["All"],
    )
    if "match_reason" not in results.columns:
        results = results.copy()
        results["match_reason"] = "Keyword / similarity match"
    st.session_state["search_results"] = results

current_inputs_changed = (
    query != st.session_state["search_query"] or
    selected_country != st.session_state["search_country"] or
    selected_status != st.session_state["search_status"] or
    selected_years != st.session_state["search_years"] or
    selected_companies != st.session_state["search_companies"] or
    top_k != st.session_state["search_top_k"]
)

if st.session_state["search_executed"] and st.session_state["search_results"] is not None:
    results = st.session_state["search_results"].copy()
    st.subheader("Results (%s)" % len(results))
    if current_inputs_changed:
        st.info("Filters or query changed. Press Search to refresh results.")
    if results.empty:
        st.warning("No matching patents found for the last search.")
    else:
        for i, (_, row) in enumerate(results.iterrows(), start=1):
            with st.container(border=True):
                st.markdown("### %s. %s" % (i, row["title"]))
                st.markdown("**Patent ID:** `%s`" % row["patent_id"])
                st.markdown("**Company:** %s" % (row["company"] if row["company"] else "Unassigned"))
                st.markdown("**Assignee:** %s" % (row["assignee"] if row["assignee"] else "Unknown"))
                st.markdown("**Inventor:** %s" % (row["inventor"] if row["inventor"] else "Unknown"))
                st.markdown("**Country / Jurisdiction:** %s" % (row["country_name"] if row["country_name"] else "Unknown"))
                st.markdown("**Status:** %s" % (row["status"] if row["status"] else "Unknown"))
                st.markdown("**Technology:** %s" % (row["top_level_tech"] if row.get("top_level_tech") else "Other / Unmapped"))
                st.markdown("**Filing Year:** %s" % (int(row["filing_year"]) if pd.notna(row["filing_year"]) else "Unknown"))
                st.info("Reason: %s" % row["match_reason"])

                c1, c2 = st.columns(2)
                with c1:
                    if pd.notna(row.get("result_link")) and str(row.get("result_link")).strip():
                        st.markdown("[Open Patent Link](%s)" % row["result_link"])
                with c2:
                    if st.button("View Details", key="view_%s" % row["patent_id"]):
                        st.session_state["selected_patent_id"] = row["patent_id"]
                        st.switch_page("pages/patent_detail.py")
else:
    st.subheader("Recently available patents")
    preview_cols = ["patent_id", "title", "company", "assignee", "inventor", "country_name", "filing_year", "status"]
    preview_cols = [c for c in preview_cols if c in df.columns]
    st.dataframe(df[preview_cols].head(20), use_container_width=True)
