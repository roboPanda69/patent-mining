import pandas as pd

DEFAULT_COMPANY = "Unassigned"

_UNKNOWN_INVENTOR_VALUES = {
    "", "unknown", "unkown", "nan", "none", "null", "n/a", "na", "-", "--"
}


def ensure_company_column(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "company" not in out.columns:
        out["company"] = DEFAULT_COMPANY
    out["company"] = (
        out["company"]
        .fillna(DEFAULT_COMPANY)
        .astype(str)
        .str.strip()
        .replace("", DEFAULT_COMPANY)
    )
    return out


def get_company_options(df: pd.DataFrame, include_all: bool = True):
    working = ensure_company_column(df)
    companies = sorted(working["company"].dropna().astype(str).str.strip().replace("", DEFAULT_COMPANY).unique().tolist())
    if include_all:
        return ["All"] + companies
    return companies


def filter_by_company(df: pd.DataFrame, selected_companies=None) -> pd.DataFrame:
    working = ensure_company_column(df)
    if not selected_companies:
        return working.copy()
    if isinstance(selected_companies, str):
        selected_companies = [selected_companies]
    if "All" in selected_companies:
        return working.copy()
    return working[working["company"].isin(selected_companies)].copy()


def split_inventor_entries(value) -> list:
    if pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    raw_parts = []
    for sep in [";", "|", "\n"]:
        text = text.replace(sep, ",")
    if " and " in text.lower():
        text = text.replace(" and ", ",")
        text = text.replace(" And ", ",")
    raw_parts.extend(text.split(","))
    cleaned = []
    for part in raw_parts:
        name = str(part).strip()
        if not name:
            continue
        if name.lower() in _UNKNOWN_INVENTOR_VALUES:
            continue
        cleaned.append(name)
    return cleaned


def inventor_count_df(df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    if "inventor" not in df.columns:
        return pd.DataFrame(columns=["inventor", "count"])
    names = []
    for value in df["inventor"]:
        names.extend(split_inventor_entries(value))
    if not names:
        return pd.DataFrame(columns=["inventor", "count"])
    series = pd.Series(names)
    out = series.value_counts().head(top_n).reset_index()
    out.columns = ["inventor", "count"]
    return out


def top_inventor_summary(df: pd.DataFrame):
    counts = inventor_count_df(df, top_n=1)
    if counts.empty:
        return None, 0
    row = counts.iloc[0]
    return row["inventor"], int(row["count"])


def format_date_ddmmyyyy(value):
    if pd.isna(value):
        return ""
    try:
        return pd.to_datetime(value).strftime("%d-%m-%Y")
    except Exception:
        return str(value)
