import os
import pandas as pd

from utils.trl_config import PATENT_PATH
from utils.trl_loader import normalize_trl_patents

INPUT_CSV = "data/trl_patents.csv"


def main():
    if not os.path.exists(INPUT_CSV):
        raise FileNotFoundError(f"Patent input not found: {INPUT_CSV}")

    raw = pd.read_csv(INPUT_CSV, low_memory=False)
    normalized = normalize_trl_patents(raw)
    normalized.to_parquet(PATENT_PATH, index=False)

    print(f"Saved -> {PATENT_PATH} | rows={len(normalized)}")
    print(normalized[["topic_name", "title", "organization_name", "year"]].head(10))


if __name__ == "__main__":
    main()
