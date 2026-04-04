import json
import re
from typing import Iterable, Optional, Tuple

import numpy as np
import pandas as pd

from utils.trl_config import TOPIC_ALIASES, TOPIC_ORDER


ACADEMIC_KEYWORDS = {
    "university", "institute", "institut", "college", "school", "laboratory",
    "lab", "academy", "centre", "center", "research", "cnrs", "mit",
}

COMPANY_STOPWORDS = {
    "inc", "corp", "corporation", "co", "company", "gmbh", "ag", "limited",
    "ltd", "llc", "plc", "sa", "bv", "kg", "pte", "motors", "motor",
}

TECH_KEYWORDS = {
    "Battery Thermal Management Systems": [
        "battery thermal", "thermal management", "cooling", "heat pipe", "liquid cooling",
        "battery pack cooling", "thermal runaway", "heat exchanger",
    ],
    "Solid-State Batteries": [
        "solid-state", "solid state", "solid electrolyte", "lithium metal", "sulfide electrolyte",
        "oxide electrolyte", "polymer electrolyte",
    ],
    "Software-Defined Vehicle (SDV)": [
        "software-defined vehicle", "software defined vehicle", "vehicle os", "vehicle operating system",
        "central compute", "zonal architecture", "over-the-air", "ota update", "domain controller",
    ],
}


def safe_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def first_existing(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    lower_map = {str(c).strip().lower(): c for c in df.columns}
    for name in candidates:
        key = str(name).strip().lower()
        if key in lower_map:
            return lower_map[key]
    return None


def normalize_topic_name(value: str) -> str:
    text = safe_text(value).lower()
    if not text:
        return "Unknown Topic"

    for canonical, aliases in TOPIC_ALIASES.items():
        if text == canonical.lower():
            return canonical
        if text in aliases:
            return canonical
        if any(alias in text for alias in aliases):
            return canonical

    for canonical, keywords in TECH_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return canonical

    return value if value else "Unknown Topic"


def derive_topic_from_text(title: str, abstract: str, fallback_topic: str = "") -> str:
    joined = f"{safe_text(fallback_topic)} {safe_text(title)} {safe_text(abstract)}".lower()
    normalized = normalize_topic_name(joined)
    if normalized != joined:
        return normalized
    return normalize_topic_name(fallback_topic) if fallback_topic else "Unknown Topic"


def parse_jsonish_list(value) -> list[str]:
    if pd.isna(value):
        return []
    if isinstance(value, list):
        return [safe_text(x) for x in value if safe_text(x)]
    text = safe_text(value)
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [safe_text(x) for x in parsed if safe_text(x)]
    except Exception:
        pass
    if "|" in text:
        return [part.strip() for part in text.split("|") if part.strip()]
    if ";" in text:
        return [part.strip() for part in text.split(";") if part.strip()]
    if "," in text:
        return [part.strip() for part in text.split(",") if part.strip()]
    return [text]


def pick_year(series: pd.Series) -> pd.Series:
    out = pd.to_numeric(series, errors="coerce")
    return out.where(out.between(1900, 2100))


def clean_org_name(value: str) -> str:
    text = safe_text(value)
    if not text:
        return "Unknown"
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ,;|")


def infer_org_type(name: str, source_type: str) -> str:
    text = clean_org_name(name).lower()
    if source_type == "paper":
        if any(keyword in text for keyword in ACADEMIC_KEYWORDS):
            return "Institution"
        return "Institution"
    if any(keyword in text for keyword in ACADEMIC_KEYWORDS):
        return "Institution"
    return "Company"


def title_keyword_summary(series: pd.Series, top_k: int = 8) -> list[str]:
    stop = {
        "the", "and", "for", "with", "from", "into", "using", "based", "system", "method", "device",
        "vehicle", "battery", "data", "analysis", "study", "review", "approach", "control", "design",
        "first", "second", "least", "configured", "thereof", "therein", "according", "one", "two",
    }
    tokens = []
    for value in series.fillna(""):
        words = re.findall(r"[A-Za-z][A-Za-z\-]{2,}", str(value).lower())
        tokens.extend([w for w in words if w not in stop])
    if not tokens:
        return []
    counts = pd.Series(tokens).value_counts().head(top_k)
    return counts.index.tolist()


def maturity_band_from_metrics(paper_count: int, patent_count: int, recent_papers: int, recent_patents: int, grant_ratio: Optional[float]) -> Tuple[str, str]:
    if paper_count <= 0 and patent_count <= 0:
        return "Insufficient Signal", "The currently available public signals are too limited to characterize maturity with confidence."

    if patent_count <= max(2, paper_count * 0.15):
        return (
            "Research-heavy",
            "The topic shows stronger academic output than patenting intensity, suggesting an earlier-stage or research-led technology area.",
        )

    if patent_count < paper_count and recent_patents > 0:
        return (
            "Translating to industry",
            "The topic shows visible academic depth with patenting momentum now building, indicating research-to-industry conversion.",
        )

    if patent_count >= paper_count * 0.75 and recent_patents >= recent_papers:
        if grant_ratio is not None and grant_ratio >= 0.35:
            return (
                "Mature / scaled",
                "Patenting is sustained and the grant mix is meaningful, indicating a more established and scaled commercialization pathway.",
            )
        return (
            "Commercializing",
            "Patenting activity is strong relative to visible research output, suggesting a technology area moving toward execution and productization.",
        )

    return (
        "Commercializing",
        "The current public signal indicates an industry-engaged topic with both technical research and patenting activity visible.",
    )


def lag_signal(paper_year_counts: pd.Series, patent_year_counts: pd.Series) -> str:
    if paper_year_counts.empty or patent_year_counts.empty:
        return "Insufficient year coverage to infer a research-to-patent transition lag."

    paper_peak_year = int(paper_year_counts.idxmax())
    patent_peak_year = int(patent_year_counts.idxmax())
    gap = patent_peak_year - paper_peak_year

    if gap >= 2:
        return f"Visible patenting peaks after research by roughly {gap} years, suggesting a meaningful research-to-industry lag."
    if gap <= -2:
        return "Patenting appears to peak before the visible paper peak, which may indicate industry-led development or incomplete research coverage in the current data."
    return "Paper and patent peaks appear relatively close, suggesting a tighter research-to-industry transition window in the current view."


def ordered_topics(values: Iterable[str]) -> list[str]:
    seen = [v for v in values if safe_text(v)]
    ordered = [t for t in TOPIC_ORDER if t in seen]
    extras = sorted([t for t in set(seen) if t not in ordered])
    return ordered + extras
