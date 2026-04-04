import re
import pandas as pd
from utils.cpc_utils import explode_cpc_sections

UNMAPPED_TECH_LABELS = {"Other / Unmapped", "Other/Unmapped", "Unmapped", "Other"}


def company_summary(df: pd.DataFrame) -> pd.DataFrame:
    if "company" not in df.columns:
        return pd.DataFrame(columns=["company", "count"])
    counts = df["company"].fillna("Unassigned").value_counts().reset_index()
    counts.columns = ["company", "count"]
    return counts


def recent_growth_summary(df: pd.DataFrame):
    if "filing_year" not in df.columns or "company" not in df.columns:
        return None
    working = df.dropna(subset=["filing_year"]).copy()
    if working.empty:
        return None
    working["filing_year"] = working["filing_year"].astype(int)
    recent_years = sorted(working["filing_year"].unique().tolist())[-3:]
    recent = working[working["filing_year"].isin(recent_years)]
    if recent.empty:
        return None
    counts = recent.groupby(["company", "filing_year"]).size().reset_index(name="count")
    growth = counts.groupby("company")["count"].agg(["first", "last"]).reset_index()
    growth["delta"] = growth["last"] - growth["first"]
    growth = growth.sort_values("delta", ascending=False)
    if growth.empty:
        return None
    row = growth.iloc[0]
    return row["company"], int(row["delta"])


def technology_distribution(df: pd.DataFrame) -> pd.DataFrame:
    if "top_level_tech" not in df.columns:
        return pd.DataFrame(columns=["top_level_tech", "count"])
    working = df[~df["top_level_tech"].fillna("Other / Unmapped").isin(UNMAPPED_TECH_LABELS)].copy()
    if working.empty:
        return pd.DataFrame(columns=["top_level_tech", "count"])
    counts = working["top_level_tech"].value_counts().reset_index()
    counts.columns = ["top_level_tech", "count"]
    return counts


def company_technology_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    if "company" not in df.columns or "top_level_tech" not in df.columns:
        return pd.DataFrame(columns=["company", "top_level_tech", "count"])
    working = df.copy()
    working["top_level_tech"] = working["top_level_tech"].fillna("Other / Unmapped")
    working = working[~working["top_level_tech"].isin(UNMAPPED_TECH_LABELS)]
    if working.empty:
        return pd.DataFrame(columns=["company", "top_level_tech", "count"])
    out = working.groupby(["company", "top_level_tech"]).size().reset_index(name="count")
    return out


def _split_inventors(text):
    if pd.isna(text):
        return []
    value = str(text).strip()
    if not value:
        return []
    parts = re.split(r";|\|| and |,", value)
    cleaned = []
    for part in parts:
        p = str(part).strip()
        if not p:
            continue
        if p.lower() in {"unknown", "unkown", "na", "n/a", "none", "nan"}:
            continue
        cleaned.append(p)
    return cleaned


def company_deep_dive(df: pd.DataFrame, company: str):
    working = df[df["company"] == company].copy()

    inventors = []
    if "inventor" in working.columns:
        for value in working["inventor"].fillna(""):
            inventors.extend(_split_inventors(value))
    inventors = pd.Series(inventors).value_counts().head(15).reset_index() if inventors else pd.DataFrame(columns=["inventor", "count"])
    if not inventors.empty:
        inventors.columns = ["inventor", "count"]

    cpc = pd.DataFrame(columns=["cpc_display", "count"])
    if "cpc_sections" in working.columns:
        cpc_df = explode_cpc_sections(working)
        if not cpc_df.empty:
            cpc = cpc_df["cpc_display"].value_counts().head(15).reset_index()
            cpc.columns = ["cpc_display", "count"]

    tech = technology_distribution(working).head(15)
    recent = working.sort_values(by=[c for c in ["filing_year", "publication_year"] if c in working.columns], ascending=False).head(20)

    return {
        "df": working,
        "inventors": inventors,
        "cpc": cpc,
        "tech": tech,
        "recent_patents": recent,
    }


def overlap_unique_tech(df: pd.DataFrame, left_company: str, right_company: str):
    if "top_level_tech" not in df.columns or "company" not in df.columns:
        return {"overlap": [], "left_only": [], "right_only": []}
    working = df.copy()
    working["top_level_tech"] = working["top_level_tech"].fillna("Other / Unmapped")
    working = working[~working["top_level_tech"].isin(UNMAPPED_TECH_LABELS)]
    left = set(working[working["company"] == left_company]["top_level_tech"].dropna().astype(str).unique().tolist())
    right = set(working[working["company"] == right_company]["top_level_tech"].dropna().astype(str).unique().tolist())
    return {
        "overlap": sorted(left & right),
        "left_only": sorted(left - right),
        "right_only": sorted(right - left),
    }


def technology_positioning_table(df: pd.DataFrame, left_company: str, right_company: str) -> pd.DataFrame:
    if "company" not in df.columns or "top_level_tech" not in df.columns:
        return pd.DataFrame(columns=["top_level_tech", left_company, right_company, "difference", "leader"])
    working = df.copy()
    working["top_level_tech"] = working["top_level_tech"].fillna("Other / Unmapped")
    working = working[~working["top_level_tech"].isin(UNMAPPED_TECH_LABELS)]
    working = working[working["company"].isin([left_company, right_company])]
    if working.empty:
        return pd.DataFrame(columns=["top_level_tech", left_company, right_company, "difference", "leader"])
    pivot = working.pivot_table(index="top_level_tech", columns="company", values="patent_id", aggfunc="count", fill_value=0).reset_index()
    for col in [left_company, right_company]:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot["difference"] = pivot[left_company] - pivot[right_company]
    pivot["leader"] = pivot.apply(lambda r: left_company if r[left_company] > r[right_company] else (right_company if r[right_company] > r[left_company] else "Balanced"), axis=1)
    pivot["total"] = pivot[left_company] + pivot[right_company]
    pivot = pivot.sort_values(["total", "difference"], ascending=[False, False]).drop(columns=["total"])
    return pivot


def leadership_messages(df: pd.DataFrame, company: str = None) -> list:
    lines = []
    working = df.copy()
    if company and "company" in working.columns:
        working = working[working["company"] == company]
    if working.empty:
        return lines

    if "filing_year" in working.columns and working["filing_year"].notna().any():
        year_counts = working["filing_year"].dropna().astype(int).value_counts().sort_index()
        latest_year = int(year_counts.index.max())
        latest_count = int(year_counts.loc[latest_year])
        lines.append(f"Recent visible activity remains live into **{latest_year}**, with **{latest_count} filings** in that year slice.")

    tech = technology_distribution(working)
    if not tech.empty:
        top = tech.iloc[0]
        lines.append(f"The clearest mapped technology concentration is **{top['top_level_tech']}**, suggesting a visible strategic emphasis in that area.")

    if "country_name" in working.columns and working["country_name"].notna().any():
        country_counts = working["country_name"].fillna("Unknown").value_counts()
        top_country = country_counts.index[0]
        top_count = int(country_counts.iloc[0])
        lines.append(f"The visible filing footprint is still anchored most strongly in **{top_country}** with **{top_count} patents**, which is useful for jurisdiction strategy discussions.")

    return lines


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
        lines.append(f"The most competitive mapped technology arena in the current view is **{top['top_level_tech']}**, which is where leadership should expect heavier innovation crowding.")
    jlr = None
    if "company" in df.columns:
        jlr_df = df[df["company"] == "JLR"]
        jlr_tech = technology_distribution(jlr_df)
        if not jlr_tech.empty:
            row = jlr_tech.iloc[0]
            jlr = (row["top_level_tech"], int(row["count"]))
    if jlr:
        lines.append(f"Within the visible JLR slice, the strongest mapped theme is **{jlr[0]}** with **{jlr[1]} patents**, which can anchor differentiation discussions.")
    return lines
