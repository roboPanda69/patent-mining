import re
import numpy as np
import pandas as pd

from utils.trl_config import TOPIC_CANONICAL_MAP, MATURITY_ORDER, INSTITUTION_HINT_WORDS, UNKNOWN_VALUES

TRL_STAGE_BANDS = [
    ("TRL-like 1-3", "Research / feasibility"),
    ("TRL-like 4-6", "Technology development / demonstration"),
    ("TRL-like 7-9", "Pilot / commercialization / scale"),
]


COUNTRY_ALIASES = {
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "united kingdom": "United Kingdom",
    "england": "United Kingdom",
    "scotland": "United Kingdom",
    "wales": "United Kingdom",
    "usa": "United States",
    "u.s.": "United States",
    "u.s.a.": "United States",
    "united states": "United States",
    "us": "United States",
    "india": "India",
    "china": "China",
    "japan": "Japan",
    "korea": "South Korea",
    "south korea": "South Korea",
    "germany": "Germany",
    "france": "France",
    "australia": "Australia",
    "canada": "Canada",
    "italy": "Italy",
    "spain": "Spain",
    "sweden": "Sweden",
    "switzerland": "Switzerland",
    "singapore": "Singapore",
}


def canonicalize_topic(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "Unknown Topic"
    key = text.lower()
    return TOPIC_CANONICAL_MAP.get(key, text)


def is_unknown(value) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip().lower() in UNKNOWN_VALUES


def looks_like_person_name(text: str) -> bool:
    text = str(text or "").strip()
    if not text or any(ch.isdigit() for ch in text):
        return False
    words = text.split()
    if len(words) not in {2, 3}:
        return False
    if any(w.lower() in INSTITUTION_HINT_WORDS for w in words):
        return False
    return all(w[:1].isupper() and w[1:].islower() for w in words if w)


def clean_institution_token(text: str) -> str:
    token = str(text or "").strip().strip("|")
    token = re.sub(r"\s+", " ", token)
    token = re.sub(r"^[,;:\-]+|[,;:\-]+$", "", token).strip()
    if not token or is_unknown(token) or looks_like_person_name(token):
        return ""
    token = re.sub(r"dept\.?", "Department", token, flags=re.I)
    token = re.sub(r"univ\.?", "University", token, flags=re.I)
    token = re.sub(r"inst\.?", "Institute", token, flags=re.I)
    token = re.sub(r"ctr\.?", "Center", token, flags=re.I)
    token = re.sub(r"lab", "Laboratory", token, flags=re.I)
    token = re.sub(r"\s+", " ", token).strip()
    parts = [p.strip() for p in token.split("|") if p.strip()]
    deduped = []
    seen = set()
    for part in parts:
        key = re.sub(r"[^a-z0-9]+", " ", part.lower()).strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(part)
    if len(deduped) == 1:
        return deduped[0]
    return " | ".join(deduped)


def split_institutions(value) -> list[str]:
    if pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    tokens = re.split(r"\||;|(?<![A-Z])/(?!\d)", text)
    result = []
    seen = set()
    for token in tokens:
        part = clean_institution_token(token)
        if not part:
            continue
        key = re.sub(r"[^a-z0-9]+", " ", part.lower()).strip()
        if key not in seen:
            seen.add(key)
            result.append(part)
    return result


def derive_country_from_institutions(institutions: list[str]) -> str:
    joined = " | ".join(institutions).lower()
    if not joined:
        return ""
    for alias, label in COUNTRY_ALIASES.items():
        if re.search(rf"{re.escape(alias)}", joined):
            return label
    return ""


def best_known_label(series: pd.Series, fallback: str = "Not clearly identified"):
    temp = series.dropna().astype(str).str.strip()
    temp = temp[~temp.str.lower().isin(UNKNOWN_VALUES)]
    if temp.empty:
        return fallback, 0
    counts = temp.value_counts()
    return counts.index[0], int(counts.iloc[0])


def maturity_band_from_metrics(paper_count: int, patent_count: int, grant_ratio: float, lag_signal: float) -> tuple[str, str]:
    if paper_count <= 0 and patent_count <= 0:
        return "Insufficient Signal", "Very limited visible paper or patent activity is available in the current dataset."
    if paper_count >= patent_count * 2 and patent_count < 40:
        return "Research-heavy", "Academic publication activity is visibly ahead of patenting, suggesting an earlier-stage technology area."
    if patent_count > 0 and paper_count > 0 and patent_count < paper_count * 1.2:
        return "Translating to industry", "Both research and patenting signals are visible, suggesting movement from academic work toward industry protection."
    if patent_count >= paper_count * 1.2 and grant_ratio < 0.45:
        return "Commercializing", "Patenting activity is strong and appears to be moving beyond pure research, although the granted share is still developing."
    return "Mature / scaled", "Patenting depth and granted share suggest a more established and scaled technology position."


def trl_stage_from_metrics(paper_count: int, patent_count: int, grant_ratio: float, company_count: int, institution_count: int) -> tuple[int, str, str]:
    total_activity = max(paper_count + patent_count, 1)
    patent_share = patent_count / total_activity
    collaboration_signal = min(company_count, 6) * 0.35 + min(institution_count, 6) * 0.15
    score = (patent_share * 5.0) + (grant_ratio * 2.0) + collaboration_signal

    if patent_count <= max(3, int(paper_count * 0.25)) and grant_ratio < 0.15:
        return 2, "TRL-like 1-3", "Research / feasibility"
    if score < 3.6:
        return 3, "TRL-like 1-3", "Research / feasibility"
    if score < 5.6:
        return 5, "TRL-like 4-6", "Technology development / demonstration"
    if score < 7.0:
        return 7, "TRL-like 7-9", "Pilot / commercialization / scale"
    return 8, "TRL-like 7-9", "Pilot / commercialization / scale"


def trl_stage_reason(stage_score: int, paper_count: int, patent_count: int, grant_ratio: float) -> str:
    if stage_score <= 3:
        return "Visible activity is still weighted toward research output, with patenting and granted protection remaining comparatively light."
    if stage_score <= 6:
        return "Both paper and patent signals are present, suggesting the topic is moving from research into demonstration, prototype, and industry translation stages."
    if grant_ratio >= 0.45:
        return "The topic shows stronger patent depth and a healthier granted share, which is more consistent with pilot, commercialization, and scaled industry activity."
    return "Patent activity is strong enough to suggest visible movement into late-stage translation and commercialization, even though granted protection is still maturing."


def papers_by_institution(papers_df: pd.DataFrame) -> pd.DataFrame:
    if papers_df.empty:
        return papers_df
    temp = papers_df.copy()
    if "institution_list" not in temp.columns:
        temp["institution_list"] = temp["organization_name"].apply(split_institutions)
    temp = temp.explode("institution_list")
    temp["institution_name"] = temp["institution_list"].fillna("").astype(str).str.strip()
    temp = temp[temp["institution_name"] != ""]
    temp = temp[~temp["institution_name"].str.lower().isin(UNKNOWN_VALUES)]
    if "country" in temp.columns:
        missing_country = temp["country"].fillna("").astype(str).str.strip() == ""
        if missing_country.any():
            temp.loc[missing_country, "country"] = temp.loc[missing_country, "institution_name"].apply(lambda x: derive_country_from_institutions([x]))
    return temp


def build_topic_metrics(normalized_df: pd.DataFrame) -> pd.DataFrame:
    if normalized_df.empty:
        return pd.DataFrame()

    rows = []
    for topic, topic_df in normalized_df.groupby("topic_name"):
        papers = topic_df[topic_df["source_type"] == "paper"].copy()
        patents = topic_df[topic_df["source_type"] == "patent"].copy()

        paper_count = len(papers)
        patent_count = len(patents)
        paper_citations = int(pd.to_numeric(papers.get("citation_count", 0), errors="coerce").fillna(0).sum()) if not papers.empty else 0
        patent_granted = int(patents.get("status", pd.Series(dtype=object)).astype(str).eq("Granted").sum()) if not patents.empty else 0
        grant_ratio = patent_granted / patent_count if patent_count else 0.0

        paper_years = pd.to_numeric(papers.get("year", pd.Series(dtype=float)), errors="coerce").dropna()
        patent_years = pd.to_numeric(patents.get("year", pd.Series(dtype=float)), errors="coerce").dropna()
        last_paper_year = int(paper_years.max()) if not paper_years.empty else np.nan
        last_patent_year = int(patent_years.max()) if not patent_years.empty else np.nan
        lag_signal = float(last_patent_year - last_paper_year) if pd.notna(last_paper_year) and pd.notna(last_patent_year) else 0.0

        papers_inst = papers_by_institution(papers)
        top_institution, top_institution_count = best_known_label(papers_inst["institution_name"]) if not papers_inst.empty else ("Not clearly identified", 0)
        top_company, top_company_count = best_known_label(patents["organization_name"]) if not patents.empty else ("Not clearly identified", 0)
        top_country, top_country_count = best_known_label(topic_df["country"], fallback="Not clearly identified")
        institution_count = int(papers_inst["institution_name"].nunique()) if not papers_inst.empty else 0
        company_count = int(patents["organization_name"].dropna().astype(str).str.strip().replace("", pd.NA).dropna().nunique()) if not patents.empty else 0

        maturity_band, maturity_reason = maturity_band_from_metrics(paper_count, patent_count, grant_ratio, lag_signal)
        trl_stage_score, trl_stage_band, trl_stage_name = trl_stage_from_metrics(
            paper_count=paper_count,
            patent_count=patent_count,
            grant_ratio=grant_ratio,
            company_count=company_count,
            institution_count=institution_count,
        )

        rows.append({
            "topic_name": topic,
            "paper_count": int(paper_count),
            "patent_count": int(patent_count),
            "paper_citations": int(paper_citations),
            "granted_patent_count": int(patent_granted),
            "grant_ratio": float(grant_ratio),
            "top_institution": top_institution,
            "top_institution_count": int(top_institution_count),
            "top_company": top_company,
            "top_company_count": int(top_company_count),
            "top_country": top_country,
            "top_country_count": int(top_country_count),
            "institution_count": institution_count,
            "company_count": company_count,
            "last_paper_year": last_paper_year,
            "last_patent_year": last_patent_year,
            "lag_signal": float(lag_signal),
            "maturity_band": maturity_band,
            "maturity_reason": maturity_reason,
            "trl_stage_score": int(trl_stage_score),
            "trl_stage_band": trl_stage_band,
            "trl_stage_name": trl_stage_name,
            "trl_stage_reason": trl_stage_reason(trl_stage_score, paper_count, patent_count, grant_ratio),
        })

    out = pd.DataFrame(rows)
    if not out.empty:
        out["maturity_band"] = pd.Categorical(out["maturity_band"], categories=MATURITY_ORDER + ["Insufficient Signal"], ordered=True)
        out = out.sort_values(["maturity_band", "patent_count", "paper_count"], ascending=[True, False, False]).reset_index(drop=True)
    return out
