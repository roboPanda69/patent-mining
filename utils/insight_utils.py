import pandas as pd
from typing import List
from utils.cpc_utils import explode_cpc_sections

UNMAPPED_TECH_LABELS = {"Other / Unmapped", "Other/Unmapped", "Unmapped", "Other"}


def safe_pct(part, whole):
    if whole == 0:
        return 0.0
    return 100.0 * part / whole


def get_top_share(series: pd.Series):
    counts = series.fillna("Unknown").value_counts()
    if counts.empty:
        return None, 0, 0.0
    top_name = counts.idxmax()
    top_count = int(counts.max())
    top_share = safe_pct(top_count, int(counts.sum()))
    return top_name, top_count, top_share


def get_top_mapped_technology(series: pd.Series):
    counts = series.fillna("Other / Unmapped").value_counts()
    if counts.empty:
        return None, 0, 0.0, 0.0

    unmapped_count = 0
    for label in UNMAPPED_TECH_LABELS:
        unmapped_count += int(counts.get(label, 0))
    unmapped_share = safe_pct(unmapped_count, int(counts.sum()))

    mapped = counts[~counts.index.isin(UNMAPPED_TECH_LABELS)]
    if mapped.empty:
        return None, 0, 0.0, unmapped_share

    top_name = mapped.idxmax()
    top_count = int(mapped.max())
    top_share = safe_pct(top_count, int(mapped.sum()))
    return top_name, top_count, top_share, unmapped_share


def build_portfolio_observations(df: pd.DataFrame) -> List[str]:
    observations = []
    if df.empty:
        return ["No patents available for the selected filters."]

    visible_company_count = df["company"].fillna("Unassigned").nunique() if "company" in df.columns else 0
    if "company" in df.columns and visible_company_count > 1:
        top_company, _, top_company_share = get_top_share(df["company"])
        if top_company:
            observations.append(
                "In the current comparison view, **%s** holds the largest visible portfolio share at about **%.1f%%** of the filtered patents." %
                (top_company, top_company_share)
            )

    if "country_name" in df.columns:
        top_country, top_country_count, top_country_share = get_top_share(df["country_name"])
        if top_country:
            observations.append(
                "The leading visible jurisdiction is **%s**, contributing **%s patents** and about **%.1f%%** of the filtered portfolio." %
                (top_country, top_country_count, top_country_share)
            )

    if "status" in df.columns:
        top_status, _, top_status_share = get_top_share(df["status"])
        if top_status:
            observations.append(
                "The dominant lifecycle position is **%s**, covering about **%.1f%%** of the visible patents." %
                (top_status, top_status_share)
            )

    if "filing_year" in df.columns and df["filing_year"].notna().any():
        year_counts = df["filing_year"].dropna().astype(int).value_counts().sort_index()
        top_year = int(year_counts.idxmax())
        top_year_share = safe_pct(int(year_counts.max()), int(year_counts.sum()))
        latest_year = int(year_counts.index.max())
        observations.append(
            "Visible filing activity is strongest around **%s**, while the latest dated activity in view extends to **%s**." %
            (top_year, latest_year)
        )

    if "top_level_tech" in df.columns:
        top_tech, top_tech_count, top_tech_share, unmapped_share = get_top_mapped_technology(df["top_level_tech"])
        if top_tech:
            observations.append(
                "Among the mapped technologies, **%s** is the clearest area of concentration with **%s patents** and about **%.1f%%** of the mapped technology slice." %
                (top_tech, top_tech_count, top_tech_share)
            )
        elif unmapped_share > 0:
            observations.append(
                "A meaningful share of the current portfolio is still outside the named technology buckets, so the technology interpretation should be treated as directional rather than final."
            )
    elif "cpc_sections" in df.columns:
        cpc_df = explode_cpc_sections(df)
        if not cpc_df.empty:
            top_bucket, _, top_bucket_share = get_top_share(cpc_df["cpc_display"])
            if top_bucket:
                observations.append(
                    "The strongest visible CPC bucket concentration is **%s**, representing about **%.1f%%** of the bucket-tagged entries." %
                    (top_bucket, top_bucket_share)
                )

    return observations
