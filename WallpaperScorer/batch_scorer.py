"""
Batch wallpaper scorer — processes a folder of images, scores each with
technical + aesthetic suites, and outputs a CSV of results.
Supports extra scoring passes (--extra N) for additional dimensions.

Usage:
    python batch_scorer.py -i Test/ -o batch_output
    python batch_scorer.py -i Test/ -o batch_output --extra 1
    python batch_scorer.py -i Test/ -o batch_output --extra 2 --extra-prompts-dir my_extra_prompts
    python cluster_by_score.py -c batch_output/scores.csv -o batch_output
"""

import os
import csv
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

BASE_FIELDNAMES = ["file_path", "technical_score", "aesthetic_score",
                   "tech_reason", "aesth_reason"]
EXTRA_SCORE_FMT = "extra_{}_score"
EXTRA_REASON_FMT = "extra_{}_reason"
DEFAULT_EXTRA_PROMPTS_DIR = "prompts_extra_default"


def find_images(folder: str) -> list[str]:
    """Return absolute paths of all image files in folder (recursive)."""
    images = []
    for root, _dirs, files in os.walk(folder):
        for f in files:
            if os.path.splitext(f)[1].lower() in IMAGE_EXTS:
                images.append(os.path.join(root, f))
    return sorted(images)


def reason_join(report: ScoreReport) -> str:
    """Concatenate all dimension reasons with their deduction values."""
    parts = [f"[{d.name} -{d.deduction}] {d.reason}" for d in report.dimensions]
    return " | ".join(parts)


def load_completed_base(csv_path: str) -> set[str]:
    """Read existing CSV and return the set of already-processed absolute paths
    (rows where technical_score is filled)."""
    if not os.path.exists(csv_path):
        return set()
    completed = set()
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            path = row.get("file_path", "").strip()
            tech = row.get("technical_score", "").strip()
            if path and tech:
                completed.add(path)
    return completed


def read_csv_rows(csv_path: str) -> tuple[list[str], list[dict]]:
    """Read CSV and return (fieldnames, rows)."""
    if not os.path.exists(csv_path):
        return list(BASE_FIELDNAMES), []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def write_csv(csv_path: str, fieldnames: list[str], rows: list[dict]):
    """Write the full CSV."""
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        f.flush()


def compute_total(row: dict) -> int:
    """Compute total_score = tech*2 + aesthetic + sum(extra_N)."""
    tech = int(row.get("technical_score", 0) or 0)
    aesth = int(row.get("aesthetic_score", 0) or 0)
    total = tech * 2 + aesth
    # Scan for extra_N_score columns
    for key in row:
        if key.startswith("extra_") and key.endswith("_score"):
            try:
                total += int(row[key] or 0)
            except (ValueError, TypeError):
                pass
    return total


# ---------------------------------------------------------------------------
# Base pass
# ---------------------------------------------------------------------------

def run_base_pass(input_dir: str, output_dir: str, debug: bool):
    """Run technical + aesthetic scoring on all images. Produce/update CSV."""
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "scores.csv")

    all_images = find_images(input_dir)
    if not all_images:
        print(f"No images found in: {input_dir}")
        return

    completed = load_completed_base(csv_path)
    images = [p for p in all_images if p not in completed]

    if completed:
        logger.info("Base pass resume: %d already completed, %d remaining (of %d total)",
                    len(completed), len(images), len(all_images))
    else:
        logger.info("Found %d image(s) in %s", len(images), input_dir)

    if not images:
        print("All images already scored — nothing to do.")
        return

    scorer_kwargs = dict(debug=debug, max_tokens=-1)
    tech_scorer = WallpaperScorer(prompts_dir="prompts", **scorer_kwargs)
    aesth_scorer = WallpaperScorer(prompts_dir="prompts_aesthetic", **scorer_kwargs)

    # Load or init CSV
    fieldnames, rows = read_csv_rows(csv_path)
    if not fieldnames:
        fieldnames = list(BASE_FIELDNAMES) + [f for f in fieldnames if f not in BASE_FIELDNAMES]
    # Ensure base fieldnames exist
    for fn in BASE_FIELDNAMES:
        if fn not in fieldnames:
            fieldnames.append(fn)

    # Build index of existing rows by file_path
    row_index = {r["file_path"]: r for r in rows}

    scored = 0
    interrupted = False

    try:
        for idx, img_path in enumerate(images, 1):
            logger.info("[%d/%d] %s", idx, len(images), os.path.basename(img_path))

            try:
                tech_report = tech_scorer.score(img_path)
                aesth_report = aesth_scorer.score(img_path)
            except Exception as e:
                logger.error("[%d/%d] Failed: %s — %s", idx, len(images), os.path.basename(img_path), e)
                continue

            tech_score = tech_report.final_score
            aesth_score = aesth_report.final_score

            # Double-perfect tiebreaker
            if tech_score == 10 and aesth_score == 10:
                logger.info("  Both 10/10 — running wallpaper fitness tiebreaker...")
                fitness_scorer = WallpaperScorer(prompts_dir="prompts", **scorer_kwargs)
                fitness_score = fitness_scorer.wallpaper_fitness_score(img_path)
                if fitness_score is not None:
                    aesth_score = fitness_score

            row = {
                "file_path": img_path,
                "technical_score": str(tech_score),
                "aesthetic_score": str(aesth_score),
                "tech_reason": reason_join(tech_report),
                "aesth_reason": reason_join(aesth_report),
            }
            row["total_score"] = str(compute_total(row))

            # Merge or append
            if img_path in row_index:
                row_index[img_path].update(row)
            else:
                row_index[img_path] = row

            scored += 1
            # Persist after each image
            write_csv(csv_path, fieldnames, list(row_index.values()))
            logger.info("  Tech: %d/10  Aesth: %d/10  Total: %s",
                        tech_score, aesth_score, row["total_score"])

    except KeyboardInterrupt:
        interrupted = True
        logger.info("Interrupted by user (Ctrl+C). Saving progress...")

    write_csv(csv_path, fieldnames, list(row_index.values()))

    print(f"\n{'=' * 50}")
    if interrupted:
        print(f"INTERRUPTED — progress saved. {scored}/{len(images)} scored this run.")
    else:
        print(f"Base pass complete: {scored}/{len(images)} scored")
    print(f"CSV: {csv_path}")
    print(f"{'=' * 50}\n")


# ---------------------------------------------------------------------------
# Extra pass
# ---------------------------------------------------------------------------

def run_extra_pass(output_dir: str, extra_index: int, extra_prompts_dir: str, debug: bool):
    """Run an additional scoring pass on already-base-scored images.

    extra_index=1: requires technical_score filled, writes extra_1_score / extra_1_reason
    extra_index=2: requires extra_1_score filled, writes extra_2_score, etc.
    """
    csv_path = os.path.join(output_dir, "scores.csv")
    if not os.path.exists(csv_path):
        logger.error("CSV not found: %s. Run base pass first.", csv_path)
        return

    fieldnames, rows = read_csv_rows(csv_path)

    # Determine prerequisite column
    if extra_index == 1:
        prereq_col = "technical_score"
    else:
        prereq_col = EXTRA_SCORE_FMT.format(extra_index - 1)

    # Check prerequisite exists in CSV
    if rows and prereq_col not in (fieldnames or []):
        logger.error(
            "Prerequisite column '%s' not found in CSV. Run pass %d first.",
            prereq_col, extra_index - 1
        )
        return

    extra_score_col = EXTRA_SCORE_FMT.format(extra_index)
    extra_reason_col = EXTRA_REASON_FMT.format(extra_index)

    # Ensure columns exist in fieldnames
    for col in [extra_score_col, extra_reason_col]:
        if col not in fieldnames:
            fieldnames.append(col)

    # Find rows needing this extra pass (have prereq, missing extra score)
    pending = []
    for r in rows:
        file_path = r.get("file_path", "").strip()
        has_prereq = r.get(prereq_col, "").strip()
        has_extra = r.get(extra_score_col, "").strip()
        if file_path and has_prereq and not has_extra:
            pending.append(r)

    if not pending:
        print(f"Extra pass {extra_index}: all rows already scored — nothing to do.")
        return

    logger.info("Extra pass %d: %d image(s) to score (prompts: %s)",
                extra_index, len(pending), extra_prompts_dir)

    scorer_kwargs = dict(debug=debug, max_tokens=-1)
    scorer = WallpaperScorer(prompts_dir=extra_prompts_dir, **scorer_kwargs)

    row_index = {r["file_path"]: r for r in rows}
    scored = 0
    interrupted = False

    try:
        for idx, row in enumerate(pending, 1):
            img_path = row["file_path"]
            logger.info("[%d/%d] %s", idx, len(pending), os.path.basename(img_path))

            if not os.path.exists(img_path):
                logger.warning("File not found, skipping: %s", img_path)
                continue

            try:
                report = scorer.score(img_path)
            except Exception as e:
                logger.error("[%d/%d] Failed: %s — %s", idx, len(pending), os.path.basename(img_path), e)
                continue

            extra_score = report.final_score
            row[extra_score_col] = str(extra_score)
            row[extra_reason_col] = reason_join(report)
            row["total_score"] = str(compute_total(row))
            row_index[img_path] = row
            scored += 1

            write_csv(csv_path, fieldnames, list(row_index.values()))
            logger.info("  Extra_%d: %d/10  Total: %s", extra_index, extra_score, row["total_score"])

    except KeyboardInterrupt:
        interrupted = True
        logger.info("Interrupted by user (Ctrl+C). Saving progress...")

    write_csv(csv_path, fieldnames, list(row_index.values()))

    print(f"\n{'=' * 50}")
    if interrupted:
        print(f"INTERRUPTED — progress saved. {scored}/{len(pending)} scored this run.")
    else:
        print(f"Extra pass {extra_index} complete: {scored}/{len(pending)} scored")
    print(f"CSV: {csv_path}")
    print(f"{'=' * 50}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Batch-score wallpapers. Supports extra passes for additional dimensions."
    )
    parser.add_argument("-i", "--input", help="Input folder of images (required for base pass)")
    parser.add_argument("-o", "--output", default="batch_output", help="Output directory (default: batch_output)")
    parser.add_argument("--extra", type=int, default=0, metavar="N",
                        help="Run extra scoring pass N (1, 2, 3...). Requires prior pass completed.")
    parser.add_argument("--extra-prompts-dir", default=DEFAULT_EXTRA_PROMPTS_DIR,
                        help=f"Prompt directory for extra pass (default: {DEFAULT_EXTRA_PROMPTS_DIR}/)")
    parser.add_argument("--debug", action="store_true", default=True)
    parser.add_argument("--no-debug", action="store_false", dest="debug")
    args = parser.parse_args()

    if args.extra > 0:
        # Extra pass — only needs output directory + CSV
        run_extra_pass(args.output, args.extra, args.extra_prompts_dir, args.debug)
    else:
        # Base pass — needs input directory
        if not args.input:
            parser.error("--input/-i is required for base pass")
        run_base_pass(args.input, args.output, args.debug)


if __name__ == "__main__":
    main()
