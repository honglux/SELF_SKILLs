"""
Batch wallpaper scorer — processes a folder of images, scores each with
technical + aesthetic suites, outputs CSV and clusters by total score.

Usage:
    python batch_scorer.py -i Test/ -o batch_output
"""

import os
import csv
import shutil
import argparse
import logging
from datetime import datetime

from AI_scorer import WallpaperScorer, ScoreReport

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("batch")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


def find_images(folder: str) -> list[str]:
    """Return absolute paths of all image files in folder (recursive)."""
    images = []
    for root, _dirs, files in os.walk(folder):
        for f in files:
            if os.path.splitext(f)[1].lower() in IMAGE_EXTS:
                images.append(os.path.join(root, f))
    return sorted(images)


def reason_join(report: ScoreReport) -> str:
    """Concatenate all dimension reasons into one string."""
    parts = [f"[{d.name}] {d.reason}" for d in report.dimensions]
    return " | ".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Batch-score wallpapers and cluster by total score."
    )
    parser.add_argument("-i", "--input", required=True, help="Input folder of images")
    parser.add_argument("-o", "--output", default="batch_output", help="Output directory (default: batch_output)")
    parser.add_argument("-f", "--full", action="store_true", help="Full-power mode: remove token limits, deep-thinking prompts")
    parser.add_argument("--debug", action="store_true", default=True)
    parser.add_argument("--no-debug", action="store_false", dest="debug")
    args = parser.parse_args()

    # Resolve mode
    if args.full:
        tech_prompts_dir = "prompts_full"
        aesth_prompts_dir = "prompts_aesthetic_full"
        max_tokens = -1
        logger.info("*** FULL POWER MODE enabled ***")
    else:
        tech_prompts_dir = "prompts"
        aesth_prompts_dir = "prompts_aesthetic"
        max_tokens = None

    input_dir = os.path.abspath(args.input)
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    images = find_images(input_dir)
    if not images:
        print(f"No images found in: {input_dir}")
        return

    logger.info("Found %d image(s) in %s", len(images), input_dir)

    # --- Init scorers ---
    scorer_kwargs = dict(debug=args.debug, max_tokens=max_tokens)
    tech_scorer = WallpaperScorer(prompts_dir=tech_prompts_dir, **scorer_kwargs)
    aesth_scorer = WallpaperScorer(prompts_dir=aesth_prompts_dir, **scorer_kwargs)

    csv_path = os.path.join(output_dir, "scores.csv")
    fieldnames = ["file_path", "technical_score", "aesthetic_score", "total_score", "tech_reason", "aesth_reason"]

    scored = 0
    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for idx, img_path in enumerate(images, 1):
            rel_path = os.path.relpath(img_path, input_dir)
            logger.info("[%d/%d] %s", idx, len(images), rel_path)

            try:
                tech_report = tech_scorer.score(img_path)
                aesth_report = aesth_scorer.score(img_path)
            except Exception as e:
                logger.error("[%d/%d] Failed: %s — %s", idx, len(images), rel_path, e)
                continue

            tech_score = tech_report.final_score
            aesth_score = aesth_report.final_score

            # --- Double-perfect tiebreaker ---
            if tech_score == 10 and aesth_score == 10:
                logger.info("  Both 10/10 — running wallpaper fitness tiebreaker...")
                fitness_scorer = WallpaperScorer(prompts_dir=tech_prompts_dir, **scorer_kwargs)
                fitness_score = fitness_scorer.wallpaper_fitness_score(img_path)
                if fitness_score is not None:
                    aesth_score = fitness_score

            total_score = int(tech_score * 2 + aesth_score)

            row = {
                "file_path": rel_path,
                "technical_score": tech_score,
                "aesthetic_score": aesth_score,
                "total_score": total_score,
                "tech_reason": reason_join(tech_report),
                "aesth_reason": reason_join(aesth_report),
            }
            writer.writerow(row)
            csvfile.flush()
            scored += 1

            # --- Cluster ---
            cluster_dir = os.path.join(output_dir, str(total_score))
            os.makedirs(cluster_dir, exist_ok=True)
            dst = os.path.join(cluster_dir, os.path.basename(img_path))
            shutil.copy2(img_path, dst)

            logger.info("  Tech: %d/10  Aesth: %d/10  Total: %d  -> %s",
                        tech_score, aesth_score, total_score,
                        os.path.relpath(cluster_dir, output_dir))

    # --- Summary ---
    print(f"\n{'=' * 50}")
    print(f"Batch complete: {scored}/{len(images)} scored")
    print(f"CSV: {csv_path}")
    print(f"Clusters: {output_dir}/")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    main()
