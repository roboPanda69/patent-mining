import os
import streamlit as st

st.set_page_config(page_title="JLR Patent Portal", layout="wide")

pages = [
    st.Page("pages/dashboard.py", title="Dashboard", icon="📊"),
    st.Page("pages/insights.py", title="Insights", icon="📈"),
    st.Page("pages/spotlight.py", title="Patent Spotlight", icon="💡"),
    st.Page("pages/technology_landscape.py", title="Technology Landscape", icon="🧭"),
    st.Page("pages/executive_summary.py", title="Executive Summary", icon="📝"),
    st.Page("pages/compare_views.py", title="Compare Views", icon="⚖️"),
    st.Page("pages/explorer.py", title="Patent Explorer", icon="📑"),
    st.Page("pages/search.py", title="Search Patents", icon="🔎"),
    st.Page("pages/patent_detail.py", title="Patent Detail", icon="🧾"),
]

if os.path.exists("pages/competitor_intelligence.py"):
    pages.append(st.Page("pages/competitor_intelligence.py", title="Competitor Intelligence", icon="🏁"))

pages.append(st.Page("pages/technology_maturity_radar.py", title="Technology Maturity Radar", icon="🛰️"))

pg = st.navigation(pages)
pg.run()
