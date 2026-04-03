import pandas as pd

COUNTRY_MAP = {
    "US": "United States",
    "GB": "United Kingdom",
    "EP": "European Patent Office",
    "WO": "WIPO / PCT",
    "CN": "China",
    "JP": "Japan",
    "IN": "India",
    "DE": "Germany",
    "KR": "South Korea",
    "FR": "France",
    "CA": "Canada",
    "AU": "Australia",
    "IT": "Italy",
    "ES": "Spain",
    "BR": "Brazil",
    "RU": "Russia",
    "MX": "Mexico",
    "NL": "Netherlands",
    "SE": "Sweden",
    "CH": "Switzerland",
}

INPUT_CSV = "gp-search-20260315-015806.csv"
OUTPUT_PARQUET = "clean_patents.parquet"
OUTPUT_CSV = "clean_patents.csv"

def ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    required_defaults = {
        "patent_id": "",
        "title": "",
        "company": "Unassigned",
        "assignee": "",
        "inventor": "",
        "result_link": "",
    }
    for col, default in required_defaults.items():
        if col not in df.columns:
            df[col] = default
    return df

def main():
    df = pd.read_csv(INPUT_CSV, skiprows=1, low_memory=False)

    df = df.rename(columns={
        "id": "patent_id",
        "inventor/author": "inventor",
        "priority date": "priority_date",
        "filing/creation date": "filing_date",
        "publication date": "publication_date",
        "grant date": "grant_date",
        "result link": "result_link",
        "representative figure link": "image_link",
    })

    df = ensure_required_columns(df)

    date_cols = ["priority_date", "filing_date", "publication_date", "grant_date"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    patent_id_series = df["patent_id"].fillna("").astype(str).str.strip().str.upper()
    df["country_code"] = patent_id_series.str.extract(r"^([A-Z]{2})", expand=False)
    df["country_name"] = df["country_code"].map(COUNTRY_MAP).fillna("Unknown")

    df["priority_year"] = df["priority_date"].dt.year
    df["filing_year"] = df["filing_date"].dt.year
    df["publication_year"] = df["publication_date"].dt.year
    df["grant_year"] = df["grant_date"].dt.year

    df["is_published"] = df["publication_date"].notna()
    df["is_granted"] = df["grant_date"].notna()

    df["status"] = "Unknown"
    df.loc[df["filing_date"].notna(), "status"] = "Filed / Unpublished"
    df.loc[df["publication_date"].notna(), "status"] = "Published Application"
    df.loc[df["grant_date"].notna(), "status"] = "Granted"

    df["company"] = (
        df["company"]
        .fillna("Unassigned")
        .astype(str)
        .str.strip()
        .replace("", "Unassigned")
    )

    df["search_text"] = (
        df["patent_id"].fillna("").astype(str) + " " +
        df["title"].fillna("").astype(str) + " " +
        df["company"].fillna("").astype(str) + " " +
        df["assignee"].fillna("").astype(str) + " " +
        df["inventor"].fillna("").astype(str) + " " +
        df["country_name"].fillna("").astype(str)
    ).str.strip()

    df = df.drop_duplicates(subset=["patent_id"], keep="first").reset_index(drop=True)

    df.to_parquet(OUTPUT_PARQUET, index=False)
    df.to_csv(OUTPUT_CSV, index=False)

    print(f"Saved -> {OUTPUT_PARQUET} | rows={len(df)}")

if __name__ == "__main__":
    main()
