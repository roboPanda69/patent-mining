import streamlit as st

st.set_page_config(page_title="Patent Intelligence Portal", layout="wide")

dashboard = st.Page("pages/dashboard.py", title="Dashboard", icon="📊")
insights = st.Page("pages/insights.py", title="Insights", icon="📈")
spotlight = st.Page("pages/spotlight.py", title="Patent Spotlight", icon="💡")
technology = st.Page("pages/technology_landscape.py", title="Technology Landscape", icon="🧭")
summary = st.Page("pages/executive_summary.py", title="Executive Summary", icon="📝")
compare = st.Page("pages/compare_views.py", title="Compare Views", icon="⚖️")
competitor = st.Page("pages/competitor_intelligence.py", title="Competitor Intelligence", icon="🏁")
explorer = st.Page("pages/explorer.py", title="Patent Explorer", icon="📑")
search = st.Page("pages/search.py", title="Search Patents", icon="🔎")
detail = st.Page("pages/patent_detail.py", title="Patent Detail", icon="🧾")

pg = st.navigation([
    dashboard,
    insights,
    spotlight,
    technology,
    summary,
    compare,
    competitor,
    explorer,
    search,
    detail,
])
pg.run()
