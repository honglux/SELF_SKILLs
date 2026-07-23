"""
Cluster images by total score — reads a scores CSV and copies images into
score-named subdirectories.

Usage as CLI:
    python cluster_by_score.py -c batch_output/scores.csv -o batch_output

Usage as library:
    from cluster_by_score import cluster_by_csv
    cluster_by_csv("batch_output/scores.csv", "clustered/")
"""

import os
import csv
import shutil
import argparse
import logging

logger = logging.getLogger("cluster")


def cluster_by_csv(csv_path: str, output_dir: str) -> int:
    """Read a scores CSV and copy each image to <output_dir>/<total_score>/.

    Returns the number of images successfully clustered.
    """
    if not os.path.exists(csv_path):
        logger.error("CSV not found: %s", csv_path)
        return 0

    os.makedirs(output_dir, exist_ok=True)
    count = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if "file_path" not in reader.fieldnames or "total_score" not in reader.fieldnames:
            logger.error(
                "CSV missing required columns. Expected: file_path, total_score. Got: %s",
                reader.fieldnames,
            )
            return 0

        for row in reader:
            img_path = row.get("file_path", "").strip()
            total_str = row.get("total_score", "").strip()

            if not img_path or not total_str:
                continue

            if not os.path.exists(img_path):
                logger.warning("File not found, skipping: %s", img_path)
                continue

            try:
                total_score = int(total_str)
            except ValueError:
                logger.warning("Invalid total_score '%s' for: %s", total_str, img_path)
                continue

            cluster_dir = os.path.join(output_dir, str(total_score))
            os.makedirs(cluster_dir, exist_ok=True)
            dst = os.path.join(cluster_dir, os.path.basename(img_path))
            shutil.copy2(img_path, dst)
            count += 1

    logger.info("Clustered %d image(s) into %s", count, output_dir)
    return count


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Cluster images by total score from a scores CSV."
    )
    parser.add_argument(
        "-c", "--csv", required=True,
        help="Path to scores CSV (must have file_path and total_score columns)",
    )
    parser.add_argument(
        "-o", "--output", default="batch_output",
        help="Output directory for score subfolders (default: batch_output)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    n = cluster_by_csv(args.csv, args.output)
    print(f"Clustered {n} image(s) into {args.output}/")


if __name__ == "__main__":
    main()
