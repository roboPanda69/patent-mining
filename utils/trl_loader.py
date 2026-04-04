import os
from typing import Any

import pandas as pd
import streamlit as st

from utils.trl_config import NORMALIZED_PATH, PAPER_PATH, PATENT_PATH
from utils.trl_utils import (
    clean_org_name,
    derive_topic_from_text,
    first_existing,
    infer_org_type,
    lag_signal,
    maturity_band_from_metrics,
    normalize_topic_name,
    ordered_topics,
    parse_jsonish_list,
    pick_year,
    safe_text,
    title_keyword_summary,
)


def _clean_common_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


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

    out = pd.DataFrame()
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
        org_candidates = []
        country_candidates = []
        for _, row in df[authorish_cols].iterrows():
            values = [safe_text(v) for v in row.tolist() if safe_text(v)]
            org_value = next((v for v in values if any(k in v.lower() for k in ["university", "institute", "college", "school", "academy", "laboratory", "centre", "center"])), "")
            org_candidates.append(clean_org_name(org_value or (values[0] if values else "Unknown")))

            country_value = next((v for v in values if len(v) in {2, 3} and v.upper() == v), "")
            country_candidates.append(country_value or "Unknown")

        out["organization_name"] = pd.Series(org_candidates, index=df.index)
        out["institution"] = pd.Series(org_candidates, index=df.index)
        out["organization_type"] = "Institution"
        out["country"] = pd.Series(country_candidates, index=df.index)

    out["topic_name"] = [
        derive_topic_from_text(title, abstract, topic)
        for title, abstract, topic in zip(out["title"], out["abstract_or_summary"], out["topic_name"])
    ]

    return out


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

    out = pd.DataFrame()
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

    return out


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
        recent_cutoff = int(topic_df["year"].dropna().max()) - 3 if topic_df["year"].dropna().any() else None
        recent_papers = int((paper_df["year"] >= recent_cutoff).sum()) if recent_cutoff is not None else 0
        recent_patents = int((patent_df["year"] >= recent_cutoff).sum()) if recent_cutoff is not None else 0

        top_institution = paper_df["organization_name"].fillna("Unknown").value_counts().idxmax() if paper_count else "N/A"
        top_company = patent_df["organization_name"].fillna("Unknown").value_counts().idxmax() if patent_count else "N/A"

        institution_diversity = int(paper_df["organization_name"].fillna("Unknown").nunique()) if paper_count else 0
        company_diversity = int(patent_df["organization_name"].fillna("Unknown").nunique()) if patent_count else 0
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
