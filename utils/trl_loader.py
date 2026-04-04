import os
import re
from typing import Any

import pandas as pd
import streamlit as st

from utils.trl_config import NORMALIZED_PATH, PAPER_PATH, PATENT_PATH
from utils.trl_utils import (
    best_known_mode,
    clean_org_name,
    derive_topic_from_text,
    first_existing,
    lag_signal,
    maturity_band_from_metrics,
    normalize_topic_name,
    ordered_topics,
    pick_year,
    safe_text,
    title_keyword_summary,
)

ACADEMIC_MARKERS = [
    "university", "institute", "institut", "college", "school", "academy", "laboratory",
    "centre", "center", "faculty", "department", "dept", "hospital", "polytechnic",
]

COUNTRY_CODE_MAP = {
    "KR": "South Korea", "HK": "Hong Kong", "CN": "China", "AU": "Australia", "CA": "Canada",
    "IE": "Ireland", "FR": "France", "IT": "Italy", "AE": "United Arab Emirates", "GB": "United Kingdom",
    "US": "United States", "DE": "Germany", "JP": "Japan", "IN": "India", "SE": "Sweden",
    "NL": "Netherlands", "CH": "Switzerland", "ES": "Spain",
}


def _clean_common_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


def _is_url_like(text: str) -> bool:
    return bool(re.match(r"^https?://", text, flags=re.I))


def _is_boolean_like(text: str) -> bool:
    return text.lower() in {"true", "false"}


def _is_country_code_like(text: str) -> bool:
    stripped = text.strip()
    return stripped.upper() in COUNTRY_CODE_MAP


def _is_plausible_org_name(text: str) -> bool:
    value = clean_org_name(text)
    lower = value.lower()
    if not value or value == "Unknown":
        return False
    if _is_url_like(value) or _is_boolean_like(value):
        return False
    if _is_country_code_like(value):
        return False
    if re.fullmatch(r"[0-9.\-]+", value):
        return False
    if any(marker in lower for marker in ACADEMIC_MARKERS):
        return True
    if len(value) < 6:
        return False
    if value.isupper() and len(value) <= 5:
        return False
    if "http" in lower or "doi" in lower or "cc-by" in lower:
        return False
    return bool(re.search(r"[A-Za-z]", value)) and (" " in value or any(ch.islower() for ch in value))


def _extract_best_paper_org_and_country(row: pd.Series) -> tuple[str, str]:
    values = [safe_text(v) for v in row.tolist() if safe_text(v)]
    org_candidates = []
    country_candidates = []

    for value in values:
        cleaned = clean_org_name(value)
        if _is_country_code_like(cleaned):
            country_candidates.append(COUNTRY_CODE_MAP.get(cleaned.upper(), cleaned.upper()))
            continue
        if _is_plausible_org_name(cleaned):
            org_candidates.append(cleaned)

    preferred_org = next((v for v in org_candidates if any(marker in v.lower() for marker in ACADEMIC_MARKERS)), "")
    org = preferred_org or (org_candidates[0] if org_candidates else "Unknown")
    country = country_candidates[0] if country_candidates else "Unknown"
    return org, country


def normalize_trl_papers(df: pd.DataFrame) -> pd.DataFrame:
    df = _clean_common_columns(df)

    topic_col = first_existing(df, ["topic", "topic_name", "theme", "query_topic"])
    title_col = first_existing(df, ["display_name", "title", "work_title"])
    abstract_col = first_existing(df, ["abstract", "abstract_text", "summary"])
    year_col = first_existing(df, ["publication_year", "year", "published_year"])
    cited_col = first_existing(df, ["cited_by_count", "citation_count", "citations"])
    doi_col = first_existing(df, ["doi"])
    type_col = first_existing(df, ["type", "publication_type"])
    paper_id_col = first_existing(df, ["id", "openalex_id", "work_id"])
    language_col = first_existing(df, ["language"])

    out = pd.DataFrame(index=df.index)
    out["topic_name"] = df[topic_col].apply(normalize_topic_name) if topic_col else "Unknown Topic"
    out["source_type"] = "paper"
    out["document_id"] = df[paper_id_col].astype(str) if paper_id_col else df.index.astype(str)
    out["title"] = df[title_col].apply(safe_text) if title_col else ""
    out["abstract_or_summary"] = df[abstract_col].apply(safe_text) if abstract_col else ""
    out["year"] = pick_year(df[year_col]) if year_col else pd.NA
    out["citation_count"] = pd.to_numeric(df[cited_col], errors="coerce").fillna(0) if cited_col else 0
    out["status"] = df[type_col].apply(safe_text) if type_col else "paper"
    out["country"] = "Unknown"
    out["organization_name"] = "Unknown"
    out["organization_type"] = "Institution"
    out["company"] = ""
    out["institution"] = "Unknown"
    out["source_link"] = df[doi_col].apply(safe_text) if doi_col else ""
    out["language"] = df[language_col].apply(safe_text) if language_col else ""

    authorish_cols = [c for c in df.columns if str(c).lower().startswith("authorship")]
    if authorish_cols:
        extracted = df[authorish_cols].apply(_extract_best_paper_org_and_country, axis=1, result_type="expand")
        extracted.columns = ["organization_name", "country"]
        out["organization_name"] = extracted["organization_name"].map(clean_org_name)
        out["institution"] = out["organization_name"]
        out["country"] = extracted["country"].fillna("Unknown").astype(str)

    out["topic_name"] = [
        derive_topic_from_text(title, abstract, topic)
        for title, abstract, topic in zip(out["title"], out["abstract_or_summary"], out["topic_name"])
    ]

    return out.reset_index(drop=True)


def normalize_trl_patents(df: pd.DataFrame) -> pd.DataFrame:
    df = _clean_common_columns(df)

    patent_id_col = first_existing(df, ["patent_id", "id"])
    topic_col = first_existing(df, ["topic", "topic_name"])
    title_col = first_existing(df, ["title"])
    abstract_col = first_existing(df, ["abstract"])
    assignee_col = first_existing(df, ["company", "assignee"])
    company_col = first_existing(df, ["company"])
    assignee_raw_col = first_existing(df, ["assignee"])
    inventor_col = first_existing(df, ["inventor", "inventor/author"])
    country_col = first_existing(df, ["country_name", "country"])
    filing_year_col = first_existing(df, ["filing_year"])
    filing_date_col = first_existing(df, ["filing_date", "filing/creation date"])
    grant_col = first_existing(df, ["grant_date"])
    status_col = first_existing(df, ["status"])
    link_col = first_existing(df, ["result_link", "source_link"])

    out = pd.DataFrame(index=df.index)
    out["topic_name"] = df[topic_col].apply(normalize_topic_name) if topic_col else "Unknown Topic"
    out["source_type"] = "patent"
    out["document_id"] = df[patent_id_col].astype(str) if patent_id_col else df.index.astype(str)
    out["title"] = df[title_col].apply(safe_text) if title_col else ""
    out["abstract_or_summary"] = df[abstract_col].apply(safe_text) if abstract_col else ""

    if filing_year_col:
        out["year"] = pick_year(df[filing_year_col])
    elif filing_date_col:
        out["year"] = pd.to_datetime(df[filing_date_col], errors="coerce").dt.year
    else:
        out["year"] = pd.NA

    out["citation_count"] = 0
    out["status"] = df[status_col].apply(safe_text) if status_col else "Unknown"
    out["country"] = df[country_col].apply(safe_text) if country_col else "Unknown"
    out["organization_name"] = df[assignee_col].apply(clean_org_name) if assignee_col else "Unknown"
    out["organization_type"] = "Company"
    out["company"] = df[company_col].apply(clean_org_name) if company_col else out["organization_name"]
    out["institution"] = ""
    out["source_link"] = df[link_col].apply(safe_text) if link_col else ""
    out["patent_status"] = out["status"]
    out["grant_flag"] = pd.to_datetime(df[grant_col], errors="coerce").notna() if grant_col else False
    out["inventor"] = df[inventor_col].apply(safe_text) if inventor_col else ""
    out["assignee_raw"] = df[assignee_raw_col].apply(safe_text) if assignee_raw_col else out["organization_name"]

    out["topic_name"] = [
        derive_topic_from_text(title, abstract, topic)
        for title, abstract, topic in zip(out["title"], out["abstract_or_summary"], out["topic_name"])
    ]

    return out.reset_index(drop=True)


def build_trl_topic_metrics(normalized: pd.DataFrame) -> pd.DataFrame:
    if normalized.empty:
        return pd.DataFrame()

    records: list[dict[str, Any]] = []
    for topic in ordered_topics(normalized["topic_name"].dropna().astype(str).unique().tolist()):
        topic_df = normalized[normalized["topic_name"] == topic].copy()
        paper_df = topic_df[topic_df["source_type"] == "paper"].copy()
        patent_df = topic_df[topic_df["source_type"] == "patent"].copy()

        paper_count = len(paper_df)
        patent_count = len(patent_df)
        year_series = topic_df["year"].dropna()
        recent_cutoff = int(year_series.max()) - 3 if not year_series.empty else None
        recent_papers = int((paper_df["year"] >= recent_cutoff).sum()) if recent_cutoff is not None else 0
        recent_patents = int((patent_df["year"] >= recent_cutoff).sum()) if recent_cutoff is not None else 0

        top_institution = best_known_mode(paper_df["organization_name"], default="Not clearly visible yet") if paper_count else "Not clearly visible yet"
        top_company = best_known_mode(patent_df["organization_name"], default="Not clearly visible yet") if patent_count else "Not clearly visible yet"

        institution_diversity = int(paper_df["organization_name"].fillna("Unknown").replace("", "Unknown").nunique()) if paper_count else 0
        company_diversity = int(patent_df["organization_name"].fillna("Unknown").replace("", "Unknown").nunique()) if patent_count else 0
        avg_citations = float(paper_df["citation_count"].fillna(0).mean()) if paper_count else 0.0
        grant_ratio = float(patent_df["grant_flag"].mean()) if patent_count and "grant_flag" in patent_df.columns else None

        paper_year_counts = paper_df.dropna(subset=["year"]).groupby("year").size().sort_index()
        patent_year_counts = patent_df.dropna(subset=["year"]).groupby("year").size().sort_index()

        research_intensity = float(paper_count * 0.6 + avg_citations * 0.4)
        patent_intensity = float(patent_count * 0.7 + (company_diversity * 0.3))

        maturity_band, maturity_reason = maturity_band_from_metrics(
            paper_count=paper_count,
            patent_count=patent_count,
            recent_papers=recent_papers,
            recent_patents=recent_patents,
            grant_ratio=grant_ratio,
        )

        records.append({
            "topic_name": topic,
            "paper_count": paper_count,
            "patent_count": patent_count,
            "top_institution": top_institution,
            "top_company": top_company,
            "institution_diversity": institution_diversity,
            "company_diversity": company_diversity,
            "avg_citations": round(avg_citations, 1),
            "grant_ratio": round(grant_ratio, 3) if grant_ratio is not None else None,
            "recent_papers": recent_papers,
            "recent_patents": recent_patents,
            "research_intensity": round(research_intensity, 2),
            "patent_intensity": round(patent_intensity, 2),
            "maturity_band": maturity_band,
            "maturity_reason": maturity_reason,
            "transition_signal": lag_signal(paper_year_counts, patent_year_counts),
            "topic_keywords": ", ".join(title_keyword_summary(topic_df["title"], top_k=6)),
        })

    return pd.DataFrame(records)


@st.cache_data
def load_trl_normalized() -> pd.DataFrame:
    if os.path.exists(NORMALIZED_PATH):
        df = pd.read_parquet(NORMALIZED_PATH)
        return df

    frames = []
    if os.path.exists(PAPER_PATH):
        frames.append(normalize_trl_papers(pd.read_parquet(PAPER_PATH)))
    if os.path.exists(PATENT_PATH):
        frames.append(normalize_trl_patents(pd.read_parquet(PATENT_PATH)))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


@st.cache_data
def load_trl_topic_metrics() -> pd.DataFrame:
    normalized = load_trl_normalized()
    if normalized.empty:
        return pd.DataFrame()
    return build_trl_topic_metrics(normalized)
