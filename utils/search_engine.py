import re
import numpy as np
import pandas as pd
import streamlit as st
from typing import Optional, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def safe_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str)

class PatentSearchEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy().reset_index(drop=True)

        self.df["patent_id"] = safe_text(self.df["patent_id"]).str.strip()
        self.df["title"] = safe_text(self.df["title"]).str.strip()
        self.df["company"] = safe_text(self.df["company"] if "company" in self.df.columns else pd.Series(["Unassigned"] * len(self.df))).str.strip()
        self.df["assignee"] = safe_text(self.df["assignee"]).str.strip()
        self.df["inventor"] = safe_text(self.df["inventor"]).str.strip()
        self.df["country_name"] = safe_text(self.df["country_name"] if "country_name" in self.df.columns else pd.Series([""] * len(self.df))).str.strip()
        self.df["status"] = safe_text(self.df["status"] if "status" in self.df.columns else pd.Series([""] * len(self.df))).str.strip()
        self.df["abstract"] = safe_text(self.df["abstract"] if "abstract" in self.df.columns else pd.Series([""] * len(self.df))).str.strip()
        self.df["cpc_codes"] = safe_text(self.df["cpc_codes"] if "cpc_codes" in self.df.columns else pd.Series([""] * len(self.df))).str.strip()
        self.df["cpc_sections"] = safe_text(self.df["cpc_sections"] if "cpc_sections" in self.df.columns else pd.Series([""] * len(self.df))).str.strip()
        self.df["patent_type"] = safe_text(self.df["patent_type"] if "patent_type" in self.df.columns else pd.Series([""] * len(self.df))).str.strip()
        self.df["top_level_tech"] = safe_text(self.df["top_level_tech"] if "top_level_tech" in self.df.columns else pd.Series([""] * len(self.df))).str.strip()

        if "filing_year" not in self.df.columns:
            self.df["filing_year"] = np.nan
        if "publication_year" not in self.df.columns:
            self.df["publication_year"] = np.nan

        self.df["title_text"] = self.df["title"]
        self.df["abstract_text"] = self.df["abstract"]
        self.df["tech_text"] = (
            self.df["top_level_tech"] + " " +
            self.df["cpc_codes"] + " " +
            self.df["cpc_sections"] + " " +
            self.df["patent_type"]
        ).str.strip()
        self.df["meta_text"] = (
            self.df["company"] + " " +
            self.df["assignee"] + " " +
            self.df["inventor"] + " " +
            self.df["country_name"] + " " +
            self.df["status"]
        ).str.strip()
        self.df["search_text"] = (
            self.df["patent_id"] + " " +
            self.df["title_text"] + " " +
            self.df["abstract_text"] + " " +
            self.df["tech_text"] + " " +
            self.df["meta_text"]
        ).str.strip()

        for col in ["patent_id", "title", "company", "assignee", "inventor", "country_name", "status", "abstract", "tech_text", "meta_text", "search_text"]:
            self.df[col + "_l"] = self.df[col].str.lower()

        self.title_vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=15000)
        self.abstract_vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=30000)
        self.tech_vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=12000)
        self.meta_vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=12000)

        self.title_matrix = self.title_vectorizer.fit_transform(self.df["title_text"])
        self.abstract_matrix = self.abstract_vectorizer.fit_transform(self.df["abstract_text"])
        self.tech_matrix = self.tech_vectorizer.fit_transform(self.df["tech_text"])
        self.meta_matrix = self.meta_vectorizer.fit_transform(self.df["meta_text"])

    def _normalize_query(self, query: str) -> str:
        return str(query).strip().lower()

    def _compact(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]", "", str(text).lower())

    def _vector_score(self, vectorizer, matrix, query: str, row_positions: np.ndarray) -> np.ndarray:
        q = self._normalize_query(query)
        if not q:
            return np.zeros(len(row_positions))
        q_vec = vectorizer.transform([q])
        sims = cosine_similarity(q_vec, matrix[row_positions]).flatten()
        return sims

    def exact_match_score_df(self, working: pd.DataFrame, query: str) -> np.ndarray:
        q = self._normalize_query(query)
        q_compact = self._compact(query)
        if not q:
            return np.zeros(len(working))
        patent_exact = ((working["patent_id_l"] == q) | (working["patent_id_l"].apply(self._compact) == q_compact)).astype(float).to_numpy()
        title_exact = (working["title_l"] == q).astype(float).to_numpy()
        patent_contains = working["patent_id_l"].str.contains(re.escape(q), na=False).astype(float).to_numpy() * 0.8
        title_contains = working["title_l"].str.contains(re.escape(q), na=False).astype(float).to_numpy() * 0.7
        return np.maximum.reduce([patent_exact, title_exact, patent_contains, title_contains])

    def metadata_field_score_df(self, working: pd.DataFrame, query: str) -> np.ndarray:
        q = self._normalize_query(query)
        if not q:
            return np.zeros(len(working))
        company_match = working["company_l"].str.contains(re.escape(q), na=False).astype(float).to_numpy() * 0.55
        assignee_match = working["assignee_l"].str.contains(re.escape(q), na=False).astype(float).to_numpy() * 0.50
        inventor_match = working["inventor_l"].str.contains(re.escape(q), na=False).astype(float).to_numpy() * 0.45
        country_match = working["country_name_l"].str.contains(re.escape(q), na=False).astype(float).to_numpy() * 0.25
        status_match = working["status_l"].str.contains(re.escape(q), na=False).astype(float).to_numpy() * 0.20
        meta_match = working["meta_text_l"].str.contains(re.escape(q), na=False).astype(float).to_numpy() * 0.35
        return np.maximum.reduce([company_match, assignee_match, inventor_match, country_match, status_match, meta_match])

    def keyword_overlap_score_df(self, working: pd.DataFrame, query: str) -> np.ndarray:
        q = self._normalize_query(query)
        if not q:
            return np.zeros(len(working))
        words = [w for w in re.findall(r"[a-z0-9]+", q) if len(w) > 1]
        if not words:
            return np.zeros(len(working))
        scores = np.zeros(len(working), dtype=float)
        for word in words:
            scores += working["search_text_l"].str.contains(r"\b%s\b" % re.escape(word), na=False).astype(float).to_numpy()
        scores = scores / max(len(words), 1)
        return np.clip(scores, 0, 1)

    def title_similarity_score_df(self, working: pd.DataFrame, query: str) -> np.ndarray:
        return self._vector_score(self.title_vectorizer, self.title_matrix, query, working.index.to_numpy())

    def abstract_similarity_score_df(self, working: pd.DataFrame, query: str) -> np.ndarray:
        return self._vector_score(self.abstract_vectorizer, self.abstract_matrix, query, working.index.to_numpy())

    def tech_similarity_score_df(self, working: pd.DataFrame, query: str) -> np.ndarray:
        return self._vector_score(self.tech_vectorizer, self.tech_matrix, query, working.index.to_numpy())

    def metadata_similarity_score_df(self, working: pd.DataFrame, query: str) -> np.ndarray:
        return self._vector_score(self.meta_vectorizer, self.meta_matrix, query, working.index.to_numpy())

    def build_match_reason(self, row: pd.Series, query: str) -> str:
        q = self._normalize_query(query)
        q_compact = self._compact(query)
        if row["patent_id_l"] == q or self._compact(row["patent_id_l"]) == q_compact:
            return "Exact patent ID match"
        if row["title_l"] == q:
            return "Exact title match"
        if q and q in row["patent_id_l"]:
            return "Patent ID contains query"
        if q and q in row["title_l"]:
            return "Title contains query"
        if q and q in row["company_l"]:
            return "Company match"
        if q and q in row["assignee_l"]:
            return "Assignee match"
        if q and q in row["inventor_l"]:
            return "Inventor match"
        if q and q in row["country_name_l"]:
            return "Country / jurisdiction match"
        if q and q in row["abstract_l"]:
            return "Abstract match"
        if q and q in row["tech_text_l"]:
            return "Technology / CPC match"
        return "Keyword / similarity match"

    def search(self, query: str, top_k: int = 15, selected_country: str = "All", selected_status: str = "All",
               selected_years: Optional[List[int]] = None, selected_companies: Optional[List[str]] = None) -> pd.DataFrame:
        working = self.df.copy()
        if selected_country != "All":
            working = working[working["country_name"] == selected_country]
        if selected_status != "All":
            working = working[working["status"] == selected_status]
        if selected_years:
            working = working[working["filing_year"].isin(selected_years)]
        if selected_companies and "All" not in selected_companies:
            working = working[working["company"].isin(selected_companies)]
        if working.empty:
            return working

        q = str(query).strip()
        if not q:
            return working.sort_values(by=["publication_year", "filing_year"], ascending=[False, False]).head(top_k).copy()

        exact_score = self.exact_match_score_df(working, q)
        field_score = self.metadata_field_score_df(working, q)
        overlap_score = self.keyword_overlap_score_df(working, q)
        title_similarity_score = self.title_similarity_score_df(working, q)
        abstract_similarity_score = self.abstract_similarity_score_df(working, q)
        tech_similarity_score = self.tech_similarity_score_df(working, q)
        meta_similarity_score = self.metadata_similarity_score_df(working, q)

        final_score = (
            0.35 * exact_score +
            0.25 * title_similarity_score +
            0.20 * abstract_similarity_score +
            0.10 * tech_similarity_score +
            0.10 * meta_similarity_score +
            0.12 * field_score +
            0.08 * overlap_score
        )

        working = working.copy()
        working["exact_score"] = exact_score
        working["field_score"] = field_score
        working["overlap_score"] = overlap_score
        working["title_similarity_score"] = title_similarity_score
        working["abstract_similarity_score"] = abstract_similarity_score
        working["tech_similarity_score"] = tech_similarity_score
        working["meta_similarity_score"] = meta_similarity_score
        working["final_score"] = final_score
        working["match_reason"] = working.apply(lambda row: self.build_match_reason(row, q), axis=1)
        return working.sort_values(by=["final_score", "publication_year", "filing_year"], ascending=[False, False, False]).head(top_k)

    def get_patent_by_id(self, patent_id: str):
        q = str(patent_id).strip().lower()
        match = self.df[self.df["patent_id_l"] == q]
        if match.empty:
            return None
        return match.iloc[0]

    def get_related_patents(self, patent_id: str, top_k: int = 8, company_mode: str = "all") -> pd.DataFrame:
        patent = self.get_patent_by_id(patent_id)
        if patent is None:
            return self.df.head(0).copy()

        working = self.df[self.df["patent_id_l"] != patent["patent_id_l"]].copy()
        if company_mode == "same_company":
            working = working[working["company"] == patent["company"]]
        elif company_mode == "other_companies":
            working = working[working["company"] != patent["company"]]
        if working.empty:
            return working

        rows = working.index.to_numpy()
        title_query = patent["title"]
        abstract_query = patent["abstract"] if patent["abstract"] else patent["title"]
        tech_query = "%s %s %s %s" % (patent["top_level_tech"], patent["cpc_codes"], patent["cpc_sections"], patent["patent_type"])
        meta_query = "%s %s %s %s" % (patent["company"], patent["assignee"], patent["country_name"], patent["status"])

        title_sim = self._vector_score(self.title_vectorizer, self.title_matrix, title_query, rows)
        abstract_sim = self._vector_score(self.abstract_vectorizer, self.abstract_matrix, abstract_query, rows)
        tech_sim = self._vector_score(self.tech_vectorizer, self.tech_matrix, tech_query, rows)
        meta_sim = self._vector_score(self.meta_vectorizer, self.meta_matrix, meta_query, rows)

        same_company = (working["company_l"] == patent["company_l"]).astype(float).to_numpy() * 0.15
        same_country = (working["country_name_l"] == patent["country_name_l"]).astype(float).to_numpy() * 0.08

        patent_year = patent.get("filing_year", np.nan)
        if pd.notna(patent_year):
            same_year_band = working["filing_year"].apply(lambda x: 1.0 if pd.notna(x) and abs(x - patent_year) <= 2 else 0.0).to_numpy() * 0.07
        else:
            same_year_band = np.zeros(len(working))

        final_related_score = 0.25 * title_sim + 0.30 * abstract_sim + 0.15 * tech_sim + 0.10 * meta_sim + same_company + same_country + same_year_band
        working = working.copy()
        working["related_score"] = final_related_score
        working["relevance_reason"] = working["company"].apply(lambda c: "Same company context" if c == patent["company"] else "Competitor context")
        return working.sort_values(by=["related_score", "publication_year", "filing_year"], ascending=[False, False, False]).head(top_k)

    def get_same_country_patents(self, patent_id: str, top_k: int = 6) -> pd.DataFrame:
        patent = self.get_patent_by_id(patent_id)
        if patent is None:
            return self.df.head(0).copy()
        country = patent["country_name_l"]
        if not country:
            return self.df.head(0).copy()
        working = self.df[(self.df["patent_id_l"] != patent["patent_id_l"]) & (self.df["country_name_l"] == country)].copy()
        return working.sort_values(by=["publication_year", "filing_year"], ascending=[False, False]).head(top_k)

    def get_latest_patents(self, top_k: int = 20) -> pd.DataFrame:
        working = self.df.copy()
        sort_cols = [c for c in ["filing_date", "publication_date", "priority_date"] if c in working.columns]
        if not sort_cols:
            return working.head(top_k)
        return working.sort_values(by=sort_cols, ascending=False).head(top_k)

    def get_daily_spotlight_patent(self):
        if self.df.empty:
            return None
        day_index = pd.Timestamp.utcnow().normalize().dayofyear % len(self.df)
        return self.df.iloc[day_index]

    def build_spotlight_summary(self, patent: pd.Series) -> dict:
        title = str(patent.get("title", "")).strip()
        company = str(patent.get("company", "")).strip() or "Unassigned"
        country = str(patent.get("country_name", "")).strip() or "Unknown jurisdiction"
        tech = str(patent.get("top_level_tech", "")).strip() or "Other / Unmapped"
        status = str(patent.get("status", "")).strip() or "Unknown status"
        filing_year = patent.get("filing_year", None)
        year_text = str(int(filing_year)) if pd.notna(filing_year) else "an unknown year"
        return {
            "what_it_is": "This spotlight patent appears under **%s** and is tagged to **%s**." % (title, company),
            "why_it_matters": "It contributes to the visible portfolio footprint in **%s** and maps into **%s** technology." % (country, tech),
            "portfolio_context": "This patent sits in **%s** lifecycle status and was filed around **%s**, which helps position it in the wider portfolio timeline." % (status, year_text),
        }

@st.cache_resource
def get_search_engine(df: pd.DataFrame) -> PatentSearchEngine:
    return PatentSearchEngine(df)
