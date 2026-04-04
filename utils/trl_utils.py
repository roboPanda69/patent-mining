import json
import re
from collections import defaultdict

import numpy as np
import pandas as pd

from utils.trl_config import TOPIC_CANONICAL_MAP, MATURITY_ORDER, INSTITUTION_HINT_WORDS, UNKNOWN_VALUES


def canonicalize_topic(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "Unknown Topic"
    key = text.lower()
    return TOPIC_CANONICAL_MAP.get(key, text)


def is_unknown(value) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip().lower() in UNKNOWN_VALUES


def looks_like_person_name(text: str) -> bool:
    text = str(text or "").strip()
    if not text or any(ch.isdigit() for ch in text):
        return False
    words = text.split()
    if len(words) not in {2, 3}:
        return False
    if any(w.lower() in INSTITUTION_HINT_WORDS for w in words):
        return False
    return all(w[:1].isupper() and w[1:].islower() for w in words if w)


def clean_institution_token(text: str) -> str:
    token = str(text or "").strip().strip("|")
    token = re.sub(r"\s+", " ", token)
    if not token or is_unknown(token) or looks_like_person_name(token):
        return ""
    parts = [p.strip() for p in token.split("|") if p.strip()]
    deduped = []
    seen = set()
    for part in parts:
        key = part.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(part)
    if len(deduped) == 1:
        return deduped[0]
    # if the repeated value is the same institution repeated many times
    normalized_unique = []
    seen = set()
    for part in deduped:
        key = re.sub(r"\s+", " ", part.lower())
        if key not in seen:
            seen.add(key)
            normalized_unique.append(part)
    return " | ".join(normalized_unique)


def split_institutions(value) -> list[str]:
    if pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    parts = [clean_institution_token(p) for p in text.split("|")]
    result = []
    seen = set()
    for part in parts:
        if not part:
            continue
        key = part.lower()
        if key not in seen:
            seen.add(key)
            result.append(part)
    return result


def best_known_label(series: pd.Series, fallback: str = "Not clearly identified"):
    temp = series.dropna().astype(str).str.strip()
    temp = temp[~temp.str.lower().isin(UNKNOWN_VALUES)]
    if temp.empty:
        return fallback, 0
    counts = temp.value_counts()
    return counts.index[0], int(counts.iloc[0])


def maturity_band_from_metrics(paper_count: int, patent_count: int, grant_ratio: float, lag_signal: float) -> tuple[str, str]:
    if paper_count <= 0 and patent_count <= 0:
        return "Insufficient Signal", "Very limited visible paper or patent activity is available in the current dataset."
    if paper_count >= patent_count * 2 and patent_count < 40:
        return "Research-heavy", "Academic publication activity is visibly ahead of patenting, suggesting an earlier-stage technology area."
    if patent_count > 0 and paper_count > 0 and patent_count < paper_count * 1.2:
        return "Translating to industry", "Both research and patenting signals are visible, suggesting movement from academic work toward industry protection."
    if patent_count >= paper_count * 1.2 and grant_ratio < 0.45:
        return "Commercializing", "Patenting activity is strong and appears to be moving beyond pure research, although the granted share is still developing."
    return "Mature / scaled", "Patenting depth and granted share suggest a more established and scaled technology position."


def build_topic_metrics(normalized_df: pd.DataFrame) -> pd.DataFrame:
    if normalized_df.empty:
        return pd.DataFrame()

    rows = []
    for topic, topic_df in normalized_df.groupby("topic_name"):
        papers = topic_df[topic_df["source_type"] == "paper"].copy()
        patents = topic_df[topic_df["source_type"] == "patent"].copy()

        paper_count = len(papers)
        patent_count = len(patents)
        top_institution, top_institution_count = best_known_label(papers["organization_name"]) if not papers.empty else ("Not clearly identified", 0)
        top_company, top_company_count = best_known_label(patents["organization_name"]) if not patents.empty else ("Not clearly identified", 0)
        grant_ratio = float(patents["is_granted"].mean()) if "is_granted" in patents.columns and not patents.empty else 0.0
        paper_year = papers["year"].dropna().median() if not papers.empty and papers["year"].notna().any() else np.nan
        patent_year = patents["year"].dropna().median() if not patents.empty and patents["year"].notna().any() else np.nan
        lag_signal = float(patent_year - paper_year) if pd.notna(paper_year) and pd.notna(patent_year) else np.nan
        maturity_band, maturity_reason = maturity_band_from_metrics(paper_count, patent_count, grant_ratio, lag_signal)

        rows.append({
            "topic_name": topic,
            "paper_count": int(paper_count),
            "patent_count": int(patent_count),
            "top_institution": top_institution,
            "top_institution_count": int(top_institution_count),
            "top_company": top_company,
            "top_company_count": int(top_company_count),
            "institution_diversity": int(papers["organization_name"].dropna().nunique()) if not papers.empty else 0,
            "company_diversity": int(patents["organization_name"].dropna().nunique()) if not patents.empty else 0,
            "paper_citations": int(papers["citation_count"].fillna(0).sum()) if not papers.empty else 0,
            "grant_ratio": grant_ratio,
            "lag_signal_years": lag_signal,
            "maturity_band": maturity_band,
            "maturity_reason": maturity_reason,
        })
    out = pd.DataFrame(rows)
    if not out.empty:
        out["maturity_band"] = pd.Categorical(out["maturity_band"], categories=MATURITY_ORDER, ordered=True)
        out = out.sort_values(["maturity_band", "topic_name"]).reset_index(drop=True)
    return out


def papers_by_institution(papers_df: pd.DataFrame) -> pd.DataFrame:
    if papers_df.empty:
        return papers_df.copy()
    if "institution_list" not in papers_df.columns:
        papers_df = papers_df.copy()
        papers_df["institution_list"] = papers_df["organization_name"].apply(split_institutions)
    exploded = papers_df.copy().explode("institution_list")
    exploded["institution_name"] = exploded["institution_list"].fillna("").astype(str).str.strip()
    exploded = exploded[exploded["institution_name"] != ""]
    return exploded


def serialise_metadata(row: dict) -> str:
    return json.dumps(row, ensure_ascii=False)
