import os
import re
import pandas as pd

from utils.trl_utils import canonicalize_topic, split_institutions

INPUT_PATH = "data/trl_papers.csv"
OUTPUT_PATH = "data/trl_papers.parquet"


TOPIC_CANDIDATES = ["topic", "Topic"]
TITLE_CANDIDATES = ["display_name", "title", "Title"]
ABSTRACT_CANDIDATES = ["abstract", "summary", "description"]
YEAR_CANDIDATES = ["publication_year", "year", "publication date", "published_year"]
CITATION_CANDIDATES = ["cited_by_count", "citation_count", "citations"]
DOI_CANDIDATES = ["doi"]
TYPE_CANDIDATES = ["type", "publication_type"]


def pick_column(df: pd.DataFrame, candidates: list[str]):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def guess_institution_column(df: pd.DataFrame):
    explicit_candidates = [
        "institution", "institutions", "institution_name", "organization_name", "affiliations", "authorship_institutions"
    ]
    for col in explicit_candidates:
        if col in df.columns:
            return col
    authorship_cols = [c for c in df.columns if str(c).lower().startswith("authorship")]
    if authorship_cols:
        # choose the column with the highest rate of pipe-separated strings / university keywords
        best_col = None
        best_score = -1
        for col in authorship_cols:
            sample = df[col].fillna("").astype(str).head(500)
            score = sample.str.contains(r"\|", regex=True).sum() + sample.str.contains(
                r"university|institute|college|school|academy|center|centre|lab|research", case=False, regex=True
            ).sum()
            if score > best_score:
                best_score = score
                best_col = col
        return best_col
    return None


def derive_country_from_institutions(institutions: list[str]) -> str:
    # leave blank for now unless a clear country token exists inside the string
    country_terms = [
        "india", "china", "japan", "korea", "united kingdom", "uk", "united states", "usa",
        "germany", "france", "australia", "canada", "italy", "spain", "sweden", "switzerland"
    ]
    joined = " | ".join(institutions).lower()
    for term in country_terms:
        if term in joined:
            if term == "uk":
                return "United Kingdom"
            if term == "usa":
                return "United States"
            return term.title()
    return ""


def main():
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(f"Missing input file: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH, low_memory=False)

    topic_col = pick_column(df, TOPIC_CANDIDATES)
    title_col = pick_column(df, TITLE_CANDIDATES)
    abstract_col = pick_column(df, ABSTRACT_CANDIDATES)
    year_col = pick_column(df, YEAR_CANDIDATES)
    citation_col = pick_column(df, CITATION_CANDIDATES)
    doi_col = pick_column(df, DOI_CANDIDATES)
    type_col = pick_column(df, TYPE_CANDIDATES)
    institution_col = guess_institution_column(df)

    out = pd.DataFrame()
    out["document_id"] = df.index.astype(str)
    out["topic_name"] = df[topic_col].apply(canonicalize_topic) if topic_col else "Unknown Topic"
    out["title"] = df[title_col].fillna("").astype(str).str.strip() if title_col else ""
    out["abstract_or_summary"] = df[abstract_col].fillna("").astype(str).str.strip() if abstract_col else ""
    out["year"] = pd.to_numeric(df[year_col], errors="coerce") if year_col else pd.NA
    out["citation_count"] = pd.to_numeric(df[citation_col], errors="coerce").fillna(0).astype(int) if citation_col else 0
    out["doi"] = df[doi_col].fillna("").astype(str).str.strip() if doi_col else ""
    out["publication_type"] = df[type_col].fillna("").astype(str).str.strip() if type_col else ""

    if institution_col:
        institution_lists = df[institution_col].apply(split_institutions)
    else:
        institution_lists = pd.Series([[] for _ in range(len(df))])

    out["institution_list"] = institution_lists
    out["organization_name"] = institution_lists.apply(lambda x: " | ".join(x))
    out["country"] = institution_lists.apply(derive_country_from_institutions)
    out["organization_type"] = "institution"
    out["source_link"] = out["doi"].apply(lambda x: f"https://doi.org/{x}" if x else "")
    out["source_type"] = "paper"

    out.to_parquet(OUTPUT_PATH, index=False)
    print(f"Saved -> {OUTPUT_PATH} | rows={len(out)}")


if __name__ == "__main__":
    main()
