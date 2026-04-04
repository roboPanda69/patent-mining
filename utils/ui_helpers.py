import pandas as pd
import streamlit as st


UNKNOWN_LABELS = {
    "", "unknown", "unassigned", "na", "n/a", "none", "nan", "null"
}


def is_unknown_value(value) -> bool:
    if pd.isna(value):
        return True
    text = str(value).strip().lower()
    return text in UNKNOWN_LABELS


def clean_named_series(series: pd.Series, fallback: str = "Unknown") -> pd.Series:
    out = series.copy()
    out = out.fillna("").astype(str).str.strip()
    out = out.replace(list(UNKNOWN_LABELS), "", regex=False)
    if (out != "").any():
        return out[out != ""]
    return pd.Series([fallback] * len(series))


def top_known_value(series: pd.Series, fallback: str = "Unknown"):
    cleaned = clean_named_series(series, fallback=fallback)
    if cleaned.empty:
        return fallback, 0
    counts = cleaned.value_counts()
    return counts.index[0], int(counts.iloc[0])


def clickable_patent_table(
    data: pd.DataFrame,
    title: str,
    key_prefix: str,
    show_cols=None,
    height: int = 400,
):
    st.subheader(title)

    if data is None or data.empty:
        st.info("No patents available in this view.")
        return

    if show_cols is None:
        show_cols = [
            "patent_id",
            "title",
            "company",
            "assignee",
            "inventor",
            "country_name",
            "filing_year",
            "status",
        ]

    available_cols = [c for c in show_cols if c in data.columns]
    display_df = data[available_cols].copy().reset_index(drop=True)

    selection_supported = True
    selected_rows = []
    try:
        event = st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=height,
            on_select="rerun",
            selection_mode="single-row",
            key=f"{key_prefix}_table",
        )
        selected_rows = event.get("selection", {}).get("rows", []) if isinstance(event, dict) else []
    except TypeError:
        selection_supported = False
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=height)

    if selection_supported and selected_rows:
        row_idx = selected_rows[0]
        id_col = "patent_id" if "patent_id" in display_df.columns else ("document_id" if "document_id" in display_df.columns else None)
        if id_col is not None:
            patent_id = str(display_df.iloc[row_idx][id_col])
            st.session_state["selected_patent_id"] = patent_id
        st.switch_page("pages/patent_detail.py")

    id_col = "patent_id" if "patent_id" in display_df.columns else ("document_id" if "document_id" in display_df.columns else None)
    patent_options = display_df[id_col].astype(str).tolist() if id_col else []
    if patent_options:
        selected_patent = st.selectbox(
            "Open patent detail",
            patent_options,
            key=f"{key_prefix}_select",
        )
        if st.button("Open Patent Detail", key=f"{key_prefix}_open"):
            st.session_state["selected_patent_id"] = selected_patent
            st.switch_page("pages/patent_detail.py")
