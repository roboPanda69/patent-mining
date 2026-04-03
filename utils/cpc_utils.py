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