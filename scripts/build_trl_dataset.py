import os
import pandas as pd

from utils.trl_config import NORMALIZED_PATH, PAPER_PATH, PATENT_PATH
from utils.trl_loader import build_trl_topic_metrics


def main():
    frames = []
    if os.path.exists(PAPER_PATH):
        frames.append(pd.read_parquet(PAPER_PATH))
    if os.path.exists(PATENT_PATH):
        frames.append(pd.read_parquet(PATENT_PATH))
    if not frames:
        raise FileNotFoundError("No TRL paper or patent parquet found. Run the preprocess scripts first.")

    normalized = pd.concat(frames, ignore_index=True)
    normalized.to_parquet(NORMALIZED_PATH, index=False)
    metrics = build_trl_topic_metrics(normalized)

    metrics_path = "data/trl_topic_metrics.parquet"
    metrics.to_parquet(metrics_path, index=False)

    print(f"Saved -> {NORMALIZED_PATH} | rows={len(normalized)}")
    print(f"Saved -> {metrics_path} | rows={len(metrics)}")


if __name__ == "__main__":
    main()
