import os
import pandas as pd

from utils.trl_utils import build_topic_metrics

PAPERS_PATH = "data/trl_papers.parquet"
PATENTS_PATH = "data/trl_patents.parquet"
NORMALIZED_PATH = "data/trl_normalized.parquet"
TOPIC_METRICS_PATH = "data/trl_topic_metrics.parquet"


def main():
    frames = []
    if os.path.exists(PAPERS_PATH):
        frames.append(pd.read_parquet(PAPERS_PATH))
    if os.path.exists(PATENTS_PATH):
        frames.append(pd.read_parquet(PATENTS_PATH))
    if not frames:
        raise FileNotFoundError("No TRL paper/patent parquet files found.")

    normalized = pd.concat(frames, ignore_index=True, sort=False)
    normalized.to_parquet(NORMALIZED_PATH, index=False)

    topic_metrics = build_topic_metrics(normalized)
    topic_metrics.to_parquet(TOPIC_METRICS_PATH, index=False)

    print(f"Saved -> {NORMALIZED_PATH} | rows={len(normalized)}")
    print(f"Saved -> {TOPIC_METRICS_PATH} | rows={len(topic_metrics)}")


if __name__ == "__main__":
    main()
