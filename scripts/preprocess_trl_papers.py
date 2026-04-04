import os
import pandas as pd

from utils.trl_config import PAPER_PATH
from utils.trl_loader import normalize_trl_papers

INPUT_CSV = "data/trl_papers.csv"


def main():
    if not os.path.exists(INPUT_CSV):
        raise FileNotFoundError(f"Paper input not found: {INPUT_CSV}")

    raw = pd.read_csv(INPUT_CSV, low_memory=False)
    normalized = normalize_trl_papers(raw)
    normalized.to_parquet(PAPER_PATH, index=False)

    print(f"Saved -> {PAPER_PATH} | rows={len(normalized)}")
    print(normalized[["topic_name", "title", "organization_name", "year"]].head(10))


if __name__ == "__main__":
    main()
