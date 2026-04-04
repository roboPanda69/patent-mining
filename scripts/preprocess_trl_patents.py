import os
import pandas as pd

from utils.trl_utils import canonicalize_topic

INPUT_PATH = "data/trl_patents.csv"
OUTPUT_PATH = "data/trl_patents.parquet"


def main():
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(f"Missing input file: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH, low_memory=False)
    rename_map = {
        "id": "document_id",
        "inventor/author": "inventor",
        "filing/creation date": "filing_date",
        "publication date": "publication_date",
        "grant date": "grant_date",
        "result link": "source_link",
        "representative figure link": "image_link",
        "company": "company",
    }
    df = df.rename(columns=rename_map)

    for col in ["priority date", "filing_date", "publication_date", "grant_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    out = pd.DataFrame()
    out["document_id"] = df["document_id"].fillna("").astype(str).str.strip()
    out["topic_name"] = df["topic"].apply(canonicalize_topic) if "topic" in df.columns else "Unknown Topic"
    out["title"] = df["title"].fillna("").astype(str).str.strip()
    out["abstract_or_summary"] = ""
    out["organization_name"] = (
        df["company"] if "company" in df.columns else df.get("assignee", "")
    )
    out["organization_name"] = out["organization_name"].fillna("").astype(str).str.strip()
    out["organization_type"] = "company"
    out["country"] = out["document_id"].str.extract(r"^([A-Z]{2})", expand=False).fillna("")
    out["year"] = pd.to_datetime(df.get("filing_date"), errors="coerce").dt.year
    out["citation_count"] = 0
    out["status"] = "Unknown"
    if "grant_date" in df.columns:
        out.loc[df["grant_date"].notna(), "status"] = "Granted"
    if "publication_date" in df.columns:
        out.loc[df["publication_date"].notna(), "status"] = "Published Application"
    out["is_granted"] = df["grant_date"].notna() if "grant_date" in df.columns else False
    out["source_link"] = df["source_link"].fillna("").astype(str).str.strip() if "source_link" in df.columns else ""
    out["assignee"] = df["assignee"].fillna("").astype(str).str.strip() if "assignee" in df.columns else ""
    out["source_type"] = "patent"

    out.to_parquet(OUTPUT_PATH, index=False)
    print(f"Saved -> {OUTPUT_PATH} | rows={len(out)}")


if __name__ == "__main__":
    main()
