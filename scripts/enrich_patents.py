import os
import re
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from utils.technology_mapper import add_technology_columns

INPUT_PATH = "clean_patents.parquet"
OUTPUT_PATH = "enriched_patents.parquet"
SAVE_EVERY = 25
REQUEST_TIMEOUT = 20
SLEEP_SECONDS = 1.0
USER_AGENT = "Mozilla/5.0 (compatible; PatentPortal/1.0)"

def safe_str(value):
    if pd.isna(value):
        return ""
    return str(value).strip()

def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    new_cols = {
        "company": "Unassigned",
        "abstract": None,
        "cpc_codes": None,
        "cpc_sections": None,
        "patent_type": None,
        "publication_number_confirmed": None,
        "application_number": None,
        "jurisdiction_confirmed": None,
        "enrichment_status": None,
        "enrichment_error": None,
        "enriched_at": None,
    }
    for col, default in new_cols.items():
        if col not in df.columns:
            df[col] = default

    df["company"] = (
        df["company"]
        .fillna("Unassigned")
        .astype(str)
        .str.strip()
        .replace("", "Unassigned")
    )
    return df

def extract_patent_details(url: str) -> dict:
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    abstract = ""
    meta_desc = soup.find("meta", attrs={"name": "DC.description"})
    if meta_desc and meta_desc.get("content"):
        abstract = meta_desc["content"].strip()

    cpc_codes = []
    for code in re.findall(r"\b[A-HY]\d{2}[A-Z]?\s*\d+(?:/\d+)?\b", page_text):
        code = re.sub(r"\s+", "", code.upper())
        if code not in cpc_codes:
            cpc_codes.append(code)

    cpc_sections = sorted({code[0] for code in cpc_codes if code})

    patent_type = ""
    if "granted patent" in page_text.lower():
        patent_type = "Granted Patent"
    elif "patent application" in page_text.lower():
        patent_type = "Patent Application"

    publication_number_confirmed = ""
    m = re.search(r"publication number\s+([A-Z0-9\-]+)", page_text, flags=re.I)
    if m:
        publication_number_confirmed = m.group(1).strip()

    application_number = ""
    m = re.search(r"application number\s+([A-Z0-9/\-]+)", page_text, flags=re.I)
    if m:
        application_number = m.group(1).strip()

    jurisdiction_confirmed = ""
    m = re.search(r"\b(US|GB|EP|WO|CN|JP|IN|DE|KR|FR|CA|AU|IT|ES|BR|RU|MX|NL|SE|CH)\b", page_text)
    if m:
        jurisdiction_confirmed = m.group(1)

    return {
        "abstract": abstract,
        "cpc_codes": ", ".join(cpc_codes) if cpc_codes else None,
        "cpc_sections": ", ".join(cpc_sections) if cpc_sections else None,
        "patent_type": patent_type or None,
        "publication_number_confirmed": publication_number_confirmed or None,
        "application_number": application_number or None,
        "jurisdiction_confirmed": jurisdiction_confirmed or None,
    }

def save_df(df: pd.DataFrame, output_path: str):
    df = add_technology_columns(df)
    df.to_parquet(output_path, index=False)
    print(f"Saved -> {output_path} | rows={len(df)}")

def main():
    if not os.path.exists(INPUT_PATH) and not os.path.exists(OUTPUT_PATH):
        raise FileNotFoundError("No input parquet found. Run preprocess_patents.py first.")

    if os.path.exists(OUTPUT_PATH):
        print("Existing enriched dataset found. Loading it to resume.")
        df = pd.read_parquet(OUTPUT_PATH)
    else:
        df = pd.read_parquet(INPUT_PATH)

    df = ensure_columns(df)

    processed_since_save = 0
    for idx in range(len(df)):
        row = df.iloc[idx]
        if safe_str(row.get("enrichment_status")) == "success":
            continue

        result_link = safe_str(row.get("result_link"))
        if not result_link:
            df.at[idx, "enrichment_status"] = "missing_link"
            df.at[idx, "enrichment_error"] = "No result_link available"
            continue

        try:
            details = extract_patent_details(result_link)
            for key, value in details.items():
                df.at[idx, key] = value
            df.at[idx, "enrichment_status"] = "success"
            df.at[idx, "enrichment_error"] = None
            df.at[idx, "enriched_at"] = pd.Timestamp.utcnow()
        except Exception as exc:
            df.at[idx, "enrichment_status"] = "error"
            df.at[idx, "enrichment_error"] = str(exc)

        processed_since_save += 1
        if processed_since_save >= SAVE_EVERY:
            save_df(df, OUTPUT_PATH)
            processed_since_save = 0

        time.sleep(SLEEP_SECONDS)

    save_df(df, OUTPUT_PATH)

if __name__ == "__main__":
    main()
