import os
import pandas as pd
import streamlit as st

from utils.trl_utils import build_topic_metrics, canonicalize_topic, split_institutions, papers_by_institution, derive_country_from_institutions

TRL_PAPERS_PATH = "data/trl_papers.parquet"
TRL_PATENTS_PATH = "data/trl_patents.parquet"
TRL_NORMALIZED_PATH = "data/trl_normalized.parquet"
TRL_TOPIC_METRICS_PATH = "data/trl_topic_metrics.parquet"


@st.cache_data
def load_trl_papers() -> pd.DataFrame:
    if not os.path.exists(TRL_PAPERS_PATH):
        return pd.DataFrame()
    df = pd.read_parquet(TRL_PAPERS_PATH).copy()
    if "topic_name" not in df.columns and "topic" in df.columns:
        df["topic_name"] = df["topic"].apply(canonicalize_topic)
    if "organization_name" in df.columns:
        df["organization_name"] = df["organization_name"].fillna("").astype(str).str.strip()
        df["organization_name"] = df["organization_name"].apply(lambda x: " | ".join(split_institutions(x)) if x else "")
    if "institution_list" not in df.columns:
        source_col = "organization_name" if "organization_name" in df.columns else pd.Series([""] * len(df))
        df["institution_list"] = source_col.apply(split_institutions)
    if "country" in df.columns:
        missing_country = df["country"].fillna("").astype(str).str.strip() == ""
        if missing_country.any():
            df.loc[missing_country, "country"] = df.loc[missing_country, "institution_list"].apply(derive_country_from_institutions)
    return df


@st.cache_data
def load_trl_patents() -> pd.DataFrame:
    if not os.path.exists(TRL_PATENTS_PATH):
        return pd.DataFrame()
    df = pd.read_parquet(TRL_PATENTS_PATH).copy()
    if "topic_name" not in df.columns and "topic" in df.columns:
        df["topic_name"] = df["topic"].apply(canonicalize_topic)
    return df


@st.cache_data
def load_trl_normalized() -> pd.DataFrame:
    if os.path.exists(TRL_NORMALIZED_PATH):
        return pd.read_parquet(TRL_NORMALIZED_PATH).copy()
    papers = load_trl_papers()
    patents = load_trl_patents()
    if papers.empty and patents.empty:
        return pd.DataFrame()
    frames = []
    if not papers.empty:
        p = papers.copy()
        p["source_type"] = "paper"
        frames.append(p)
    if not patents.empty:
        t = patents.copy()
        t["source_type"] = "patent"
        frames.append(t)
    return pd.concat(frames, ignore_index=True, sort=False)


@st.cache_data
def load_trl_topic_metrics() -> pd.DataFrame:
    if os.path.exists(TRL_TOPIC_METRICS_PATH):
        metrics = pd.read_parquet(TRL_TOPIC_METRICS_PATH).copy()
        required = {"trl_stage_score", "trl_stage_band", "trl_stage_name", "trl_stage_reason"}
        if required.issubset(metrics.columns):
            return metrics
    normalized = load_trl_normalized()
    return build_topic_metrics(normalized)


@st.cache_data
def load_trl_papers_by_institution() -> pd.DataFrame:
    papers = load_trl_papers()
    if papers.empty:
        return papers
    return papers_by_institution(papers)
