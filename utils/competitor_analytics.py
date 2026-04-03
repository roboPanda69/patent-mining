import pandas as pd
from utils.company_utils import inventor_count_df
from utils.cpc_utils import explode_cpc_sections

def _safe_count(df, col):
    return int(df[col].nunique()) if col in df.columns else 0

def company_summary(df: pd.DataFrame) -> pd.DataFrame:
    if "company" not in df.columns:
        return pd.DataFrame(columns=["company", "count"])
    out = df["company"].fillna("Unassigned").value_counts().reset_index()
    out.columns = ["company", "count"]
    return out

def recent_growth_summary(df: pd.DataFrame, recent_years: int = 3):
    if "company" not in df.columns or "filing_year" not in df.columns:
        return None
    working = df.dropna(subset=["filing_year"]).copy()
    if working.empty:
        return None
    working["filing_year"] = working["filing_year"].astype(int)
    max_year = int(working["filing_year"].max())
    min_recent = max_year - recent_years + 1
    recent = working[working["filing_year"] >= min_recent]
    earlier = working[working["filing_year"] < min_recent]
    recent_counts = recent["company"].value_counts()
    earlier_counts = earlier["company"].value_counts()
    growth = (recent_counts - earlier_counts.reindex(recent_counts.index).fillna(0)).sort_values(ascending=False)
    if growth.empty:
        return None
    return growth.index[0], int(growth.iloc[0])

def technology_distribution(df: pd.DataFrame) -> pd.DataFrame:
    if "top_level_tech" not in df.columns:
        return pd.DataFrame(columns=["top_level_tech", "count"])
    out = df["top_level_tech"].fillna("Other / Unmapped").value_counts().reset_index()
    out.columns = ["top_level_tech", "count"]
    return out

def jlr_strongest_tech(df: pd.DataFrame):
    if "company" not in df.columns or "top_level_tech" not in df.columns:
        return None
    jlr = df[df["company"] == "JLR"]
    if jlr.empty:
        return None
    counts = jlr["top_level_tech"].fillna("Other / Unmapped").value_counts()
    if counts.empty:
        return None
    return counts.idxmax(), int(counts.max())

def company_technology_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    if "company" not in df.columns or "top_level_tech" not in df.columns:
        return pd.DataFrame(columns=["company", "top_level_tech", "count"])
    out = df.groupby(["company", "top_level_tech"]).size().reset_index(name="count")
    return out

def top_cpc_for_company(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    cpc_df = explode_cpc_sections(df)
    if cpc_df.empty:
        return pd.DataFrame(columns=["cpc_display", "count"])
    out = cpc_df["cpc_display"].value_counts().head(top_n).reset_index()
    out.columns = ["cpc_display", "count"]
    return out

def deep_dive_keywords(df: pd.DataFrame, top_n: int = 12) -> pd.DataFrame:
    text = (
        df["title"].fillna("").astype(str) + " " +
        df.get("abstract", pd.Series([""] * len(df))).fillna("").astype(str)
    ).str.lower()
    stopwords = {
        "the", "and", "for", "with", "from", "that", "this", "method", "system", "vehicle",
        "patent", "apparatus", "control", "data", "device", "based", "using", "into", "over"
    }
    counts = {}
    for value in text:
        for token in value.split():
            token = "".join(ch for ch in token if ch.isalnum() or ch == "-").strip("-")
            if len(token) < 4 or token in stopwords:
                continue
            counts[token] = counts.get(token, 0) + 1
    if not counts:
        return pd.DataFrame(columns=["keyword", "count"])
    out = pd.Series(counts).sort_values(ascending=False).head(top_n).reset_index()
    out.columns = ["keyword", "count"]
    return out

def company_deep_dive(df: pd.DataFrame, company: str) -> dict:
    working = df[df["company"] == company].copy()
    return {
        "df": working,
        "inventors": inventor_count_df(working, top_n=10),
        "cpc": top_cpc_for_company(working, top_n=10),
        "tech": technology_distribution(working).head(10),
        "keywords": deep_dive_keywords(working, top_n=12),
    }

def overlap_unique_tech(df: pd.DataFrame, left_company: str, right_company: str) -> dict:
    if "top_level_tech" not in df.columns:
        return {"overlap": [], "left_only": [], "right_only": []}
    left = set(df[df["company"] == left_company]["top_level_tech"].dropna().astype(str))
    right = set(df[df["company"] == right_company]["top_level_tech"].dropna().astype(str))
    return {
        "overlap": sorted(left & right),
        "left_only": sorted(left - right),
        "right_only": sorted(right - left),
    }

def competitor_insight_lines(df: pd.DataFrame) -> list:
    lines = []
    company_counts = company_summary(df)
    if not company_counts.empty:
        leader = company_counts.iloc[0]
        lines.append(f"**{leader['company']}** currently has the largest visible portfolio in this filtered view with **{int(leader['count'])} patents**.")
    growth = recent_growth_summary(df)
    if growth:
        lines.append(f"Recent filing momentum appears strongest for **{growth[0]}**, which shows the largest visible increase across the latest filing window.")
    tech = technology_distribution(df)
    if not tech.empty:
        top = tech.iloc[0]
        lines.append(f"The most crowded visible technology area is **{top['top_level_tech']}**, indicating heavier competitive activity in that domain.")
    jlr = jlr_strongest_tech(df)
    if jlr:
        lines.append(f"Within the visible JLR slice, the strongest technology area appears to be **{jlr[0]}** with **{jlr[1]} patents**.")
    return lines
