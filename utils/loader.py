import os
import pandas as pd
import streamlit as st
from utils.company_utils import ensure_company_column
from utils.technology_mapper import add_technology_columns

ENRICHED_PATH = "data/enriched_patents.parquet"
CLEAN_PATH = "data/clean_patents.parquet"

def normalize_status(row: pd.Series) -> str:
    grant_date = row.get("grant_date")
    publication_date = row.get("publication_date")
    filing_date = row.get("filing_date")
    if pd.notna(grant_date):
        return "Granted"
    if pd.notna(publication_date):
        return "Published Application"
    if pd.notna(filing_date):
        return "Filed / Unpublished"
    return "Unknown"

@st.cache_data
def load_patents() -> pd.DataFrame:
    path = ENRICHED_PATH if os.path.exists(ENRICHED_PATH) else CLEAN_PATH
    if not os.path.exists(path):
        raise FileNotFoundError("No patent dataset found. Please generate clean or enriched parquet files first.")

    df = pd.read_parquet(path).copy()

    date_cols = ["priority_date", "filing_date", "publication_date", "grant_date", "enriched_at"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if "priority_year" not in df.columns and "priority_date" in df.columns:
        df["priority_year"] = df["priority_date"].dt.year
    if "filing_year" not in df.columns and "filing_date" in df.columns:
        df["filing_year"] = df["filing_date"].dt.year
    if "publication_year" not in df.columns and "publication_date" in df.columns:
        df["publication_year"] = df["publication_date"].dt.year
    if "grant_year" not in df.columns and "grant_date" in df.columns:
        df["grant_year"] = df["grant_date"].dt.year

    if "is_published" not in df.columns and "publication_date" in df.columns:
        df["is_published"] = df["publication_date"].notna()
    if "is_granted" not in df.columns and "grant_date" in df.columns:
        df["is_granted"] = df["grant_date"].notna()

    df["status"] = df.apply(normalize_status, axis=1)
    df = ensure_company_column(df)
    df = add_technology_columns(df)

    for col in ["patent_id", "title", "assignee", "inventor", "country_name", "result_link", "abstract", "cpc_codes", "cpc_sections", "patent_type"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df
