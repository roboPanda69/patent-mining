import ast
import pandas as pd
import streamlit as st
import plotly.express as px
from utils.loader import load_patents
from utils.cpc_utils import explode_cpc_sections
from utils.insight_utils import build_portfolio_observations

st.title("Executive Summary")
st.caption("A communication-friendly summary of the patent portfolio for leadership and stakeholders.")

df = load_patents().copy()

def parse_list_like(value):
    if pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass
    return [x.strip() for x in text.split(",") if x.strip()]

def explode_column(data: pd.DataFrame, col: str, new_col: str):
    temp = data.copy()
    temp[new_col] = temp[col].apply(parse_list_like)
    temp = temp.explode(new_col)
    temp[new_col] = temp[new_col].fillna("").astype(str).str.strip()
    temp = temp[temp[new_col] != ""]
    return temp

# ---------------------------------------------------
# Sidebar filters
# ---------------------------------------------------
st.sidebar.header("Summary Filters")

country_options = ["All"] + sorted(df["country_name"].dropna().astype(str).unique().tolist()) if "country_name" in df.columns else ["All"]
status_options = ["All"] + sorted(df["status"].dropna().astype(str).unique().tolist()) if "status" in df.columns else ["All"]
year_options = sorted(df["filing_year"].dropna().astype(int).unique().tolist()) if "filing_year" in df.columns else []

selected_country = st.sidebar.selectbox("Country / Jurisdiction", country_options)
selected_status = st.sidebar.selectbox("Status", status_options)
selected_years = st.sidebar.multiselect("Filing Year", year_options)

filtered = df.copy()

if selected_country != "All" and "country_name" in filtered.columns:
    filtered = filtered[filtered["country_name"] == selected_country]

if selected_status != "All" and "status" in filtered.columns:
    filtered = filtered[filtered["status"] == selected_status]

if selected_years and "filing_year" in filtered.columns:
    filtered = filtered[filtered["filing_year"].isin(selected_years)]

if filtered.empty:
    st.warning("No patents found for the selected filters.")
    st.stop()

# ---------------------------------------------------
# KPI cards
# ---------------------------------------------------
total_patents = len(filtered)
granted = int(filtered["is_granted"].sum()) if "is_granted" in filtered.columns else 0
published = int(filtered["is_published"].sum()) if "is_published" in filtered.columns else 0
countries = int(filtered["country_name"].fillna("Unknown").nunique()) if "country_name" in filtered.columns else 0
assignees = int(filtered["assignee"].fillna("Unknown").nunique()) if "assignee" in filtered.columns else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Patents", total_patents)
c2.metric("Granted", granted)
c3.metric("Published", published)
c4.metric("Countries", countries)
c5.metric("Assignees", assignees)

st.divider()

# ---------------------------------------------------
# Compute summary observations
# ---------------------------------------------------
observations = build_portfolio_observations(filtered)

# ---------------------------------------------------
# Leadership summary card
# ---------------------------------------------------
st.subheader("Leadership Narrative")

narrative_parts = []

if observations:
    narrative_parts.append(" ".join(observations[:3]))

if "country_name" in filtered.columns and filtered["country_name"].notna().any():
    country_counts = filtered["country_name"].fillna("Unknown").value_counts().head(3)
    country_text = ", ".join([f"{idx} ({val})" for idx, val in country_counts.items()])
    narrative_parts.append(f"Top jurisdictions in this view are {country_text}.")

if "assignee" in filtered.columns and filtered["assignee"].notna().any():
    assignee_counts = filtered["assignee"].fillna("Unknown").value_counts().head(3)
    assignee_text = ", ".join([f"{idx} ({val})" for idx, val in assignee_counts.items()])
    narrative_parts.append(f"Top assignee entries are {assignee_text}.")

leadership_message = " ".join(narrative_parts) if narrative_parts else "The current filtered portfolio provides a directional view of where activity and concentration are most visible."
st.success(leadership_message)

st.subheader("Key Messages")
for obs in observations[:6]:
    st.info(obs)

st.divider()
st.subheader("Portfolio Themes")

theme_cards = st.columns(3)

# Theme 1: Geography
with theme_cards[0]:
    if "country_name" in filtered.columns and filtered["country_name"].notna().any():
        country_counts = filtered["country_name"].fillna("Unknown").value_counts()
        top_country = country_counts.idxmax()
        st.markdown("### Geographic Theme")
        st.write(
            f"The portfolio is currently led by **{top_country}**, making it the strongest visible jurisdiction in this filtered view."
        )

# Theme 2: Technology
with theme_cards[1]:
    if "cpc_sections" in filtered.columns:
        cpc_df = explode_cpc_sections(filtered)
        if not cpc_df.empty:
            bucket_counts = cpc_df["cpc_display"].value_counts()
            top_bucket = bucket_counts.idxmax()
            st.markdown("### Technology Theme")
            st.write(
                f"The most visible technology bucket is **{top_bucket}**, showing where the current portfolio is most concentrated."
            )

# Theme 3: Lifecycle
with theme_cards[2]:
    if "status" in filtered.columns and filtered["status"].notna().any():
        status_counts = filtered["status"].fillna("Unknown").value_counts()
        top_status = status_counts.idxmax()
        st.markdown("### Lifecycle Theme")
        st.write(
            f"The portfolio is currently dominated by **{top_status}** entries, which shapes how mature the visible set appears."
        )

# ---------------------------------------------------
# Communication-friendly charts
# ---------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("Jurisdiction Share")
    if "country_name" in filtered.columns and filtered["country_name"].notna().any():
        country_counts = filtered["country_name"].fillna("Unknown").value_counts().head(10).reset_index()
        country_counts.columns = ["country_name", "count"]
        fig = px.bar(country_counts, x="country_name", y="count", labels={"country_name": "Country", "count": "Patent Count"})
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Status Mix")
    if "status" in filtered.columns and filtered["status"].notna().any():
        status_counts = filtered["status"].fillna("Unknown").value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        fig = px.pie(status_counts, names="status", values="count")
        st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)

with left:
    st.subheader("Filing Activity Over Time")
    if "filing_year" in filtered.columns and filtered["filing_year"].notna().any():
        year_counts = filtered["filing_year"].dropna().astype(int).value_counts().sort_index().reset_index()
        year_counts.columns = ["filing_year", "count"]
        fig = px.line(year_counts, x="filing_year", y="count", markers=True)
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Top Assignees")
    if "assignee" in filtered.columns and filtered["assignee"].notna().any():
        assignee_counts = filtered["assignee"].fillna("Unknown").value_counts().head(10).reset_index()
        assignee_counts.columns = ["assignee", "count"]
        fig = px.bar(assignee_counts, x="count", y="assignee", orientation="h")
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------
# Summary table for export / reporting
# ---------------------------------------------------
st.subheader("Summary Table")

summary_table = pd.DataFrame({
    "Metric": [
        "Total Patents",
        "Granted",
        "Published",
        "Countries",
        "Assignees"
    ],
    "Value": [
        total_patents,
        granted,
        published,
        countries,
        assignees
    ]
})

st.dataframe(summary_table, use_container_width=True)
