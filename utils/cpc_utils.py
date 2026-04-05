import ast
import pandas as pd

CPC_SECTION_LABELS = {
    "A": "Human Necessities",
    "B": "Transport / Operations / Mechanical",
    "C": "Chemistry / Metallurgy",
    "D": "Textiles / Paper",
    "E": "Fixed Constructions / Infrastructure",
    "F": "Mechanical Engineering / Lighting / Heating / Weapons",
    "G": "Physics / Sensing / Computing / Control",
    "H": "Electricity / Electronics / Communication",
    "Y": "Cross-sectional / Emerging Technologies",
}


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


def section_label(section: str) -> str:
    section = str(section).strip().upper()
    if not section:
        return "Unknown"
    return CPC_SECTION_LABELS.get(section, f"{section} / Other")


def explode_cpc_sections(df: pd.DataFrame) -> pd.DataFrame:
    temp = df.copy()
    temp["cpc_section"] = temp["cpc_sections"].apply(parse_list_like)
    temp = temp.explode("cpc_section")
    temp["cpc_section"] = temp["cpc_section"].fillna("").astype(str).str.strip().str.upper()
    temp = temp[temp["cpc_section"] != ""]
    temp["cpc_section_label"] = temp["cpc_section"].apply(section_label)
    temp["cpc_display"] = temp["cpc_section"] + " — " + temp["cpc_section_label"]
    return temp


def summarize_cpc_signal(cpc_df: pd.DataFrame) -> str:
    if cpc_df is None or cpc_df.empty or "cpc_display" not in cpc_df.columns:
        return "No CPC signal is visible in the current view."

    counts = cpc_df["cpc_display"].value_counts()
    if counts.empty:
        return "No CPC signal is visible in the current view."

    top_bucket = counts.index[0]
    top_count = int(counts.iloc[0])
    total = int(counts.sum())
    share = top_count / total if total else 0
    unique_buckets = int(counts.shape[0])

    if share >= 0.45:
        return f"The strongest CPC signal in the current view is **{top_bucket}**, representing roughly **{share:.0%}** of visible CPC bucket assignments."
    if unique_buckets <= 3:
        return f"The current view is concentrated across a small set of CPC buckets, led by **{top_bucket}**."
    return f"The current view is spread across multiple CPC buckets, with **{top_bucket}** emerging as the leading CPC signal rather than a single dominant cluster."
