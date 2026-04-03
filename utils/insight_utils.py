import pandas as pd
from typing import List
from utils.cpc_utils import explode_cpc_sections

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

def build_portfolio_observations(df: pd.DataFrame) -> List[str]:
    observations = []
    if df.empty:
        return ["No patents available for the selected filters."]

    if "company" in df.columns:
        top_company, _, top_company_share = get_top_share(df["company"])
        if top_company:
            observations.append("The largest visible company slice is **%s**, representing about **%.1f%%** of the filtered patents." % (top_company, top_company_share))

    if "country_name" in df.columns:
        top_country, _, top_country_share = get_top_share(df["country_name"])
        if top_country:
            observations.append("The leading jurisdiction is **%s**, contributing about **%.1f%%** of the filtered portfolio." % (top_country, top_country_share))

    if "status" in df.columns:
        top_status, _, top_status_share = get_top_share(df["status"])
        if top_status:
            observations.append("The dominant lifecycle stage is **%s**, covering about **%.1f%%** of the visible patents." % (top_status, top_status_share))

    if "filing_year" in df.columns and df["filing_year"].notna().any():
        year_counts = df["filing_year"].dropna().astype(int).value_counts().sort_index()
        top_year = int(year_counts.idxmax())
        top_year_share = safe_pct(int(year_counts.max()), int(year_counts.sum()))
        observations.append("The strongest visible filing concentration appears around **%s**, representing about **%.1f%%** of the dated filings." % (top_year, top_year_share))

    if "top_level_tech" in df.columns:
        top_tech, _, top_tech_share = get_top_share(df["top_level_tech"])
        if top_tech:
            observations.append("The most visible technology concentration is **%s**, contributing about **%.1f%%** of the current view." % (top_tech, top_tech_share))
    elif "cpc_sections" in df.columns:
        cpc_df = explode_cpc_sections(df)
        if not cpc_df.empty:
            top_bucket, _, top_bucket_share = get_top_share(cpc_df["cpc_display"])
            if top_bucket:
                observations.append("The strongest visible technology concentration is in **%s**, representing about **%.1f%%** of the bucket-tagged entries." % (top_bucket, top_bucket_share))

    return observations
