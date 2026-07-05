"""
WallpaperScorer — Multi-dimension AI-powered wallpaper aesthetic evaluator.

Usage as CLI:
    python AI_scorer.py -i image.png

Usage as library:
    from AI_scorer import WallpaperScorer
    scorer = WallpaperScorer()
    report = scorer.score("image.png")
    scorer.print_report(report)
"""

import os
import re
import json
import glob
import base64
import argparse
import logging
from datetime import datetime
from dataclasses import dataclass, field
from openai import OpenAI

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("WallpaperScorer")
logger.setLevel(logging.INFO)
logger.propagate = False  # prevent duplicate logs when imported by batch scripts

_FH = logging.FileHandler(
    os.path.join(LOG_DIR, f"scoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    encoding="utf-8",
)
_FH.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
_SH = logging.StreamHandler()
_SH.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_FH)
logger.addHandler(_SH)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class DimensionResult:
    """A single dimension's scoring outcome."""
    name: str
    reason: str
    deduction: float
    recovered: bool = False


@dataclass
class ScoreReport:
    """Aggregated scoring report for one image."""
    image_path: str
    dimensions: list[DimensionResult] = field(default_factory=list)
    total_deduction: float = 0.0
    final_score: int = 10

    @property
    def recovered_count(self) -> int:
        return sum(1 for d in self.dimensions if d.recovered)


# ---------------------------------------------------------------------------
# WallpaperScorer
# ---------------------------------------------------------------------------

class WallpaperScorer:
    """Scoring engine that evaluates wallpaper images across multiple
    dimensions using separate per-dimension prompts and aggregates the result."""

    # Paths
    DEFAULT_PROMPTS_DIR = "prompts"

    # API defaults
    DEFAULT_BASE_URL = "http://localhost:1234/v1"
    DEFAULT_API_KEY = "lm-studio"
    DEFAULT_MODEL = "local-model"

    # Token budgets (overridden by constructor if --full mode)
    DEFAULT_MAX_TOKENS = 4096

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str = DEFAULT_API_KEY,
        model: str = DEFAULT_MODEL,
        prompts_dir: str = DEFAULT_PROMPTS_DIR,
        debug: bool = True,
        timeout: int = 1800,
        max_retries: int = 0,
        max_tokens: int | None = None,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.prompts_dir = prompts_dir
        self.debug = debug
        self.max_tokens = max_tokens if max_tokens is not None else self.DEFAULT_MAX_TOKENS
        # Resolve fallback/fitness prompts relative to prompts_dir
        self._fallback_prompt_path = os.path.join(prompts_dir, "_fallback_recover.md")
        self._fitness_prompt_path = os.path.join(prompts_dir, "_wallpaper_fitness.md")
        self._client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            max_retries=max_retries,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(self, image_path: str) -> ScoreReport:
        """Score a wallpaper image across all dimensions.

        Returns a ScoreReport with per-dimension details and final score.
        """
        prompts = self._load_prompts()
        image_b64 = self._encode_image(image_path)

        report = ScoreReport(image_path=image_path)

        for p in prompts:
            result = self._score_dimension(p["name"], p["content"], image_b64)
            report.dimensions.append(result)

        report.total_deduction = sum(d.deduction for d in report.dimensions)
        raw = 10.0 - report.total_deduction
        report.final_score = max(1, int(raw // 1))
        return report

    def print_report(self, report: ScoreReport):
        """Pretty-print a ScoreReport to stdout."""
        print(f"\n{'=' * 60}")
        print(f"File: {os.path.basename(report.image_path)}")
        print(f"{'=' * 60}")
        for d in report.dimensions:
            tag = " [RECOVERED]" if d.recovered else ""
            print(f"  [{d.name}]{tag}  deduction: {d.deduction}")
            print(f"           reason: {d.reason}")
        print(f"{'=' * 60}")
        print(f"  Total deduction: {report.total_deduction}")
        print(f"  Final score:      {report.final_score}/10")
        if report.recovered_count:
            print(f"  Recovered:        {report.recovered_count} dimension(s)")
        print(f"{'=' * 60}\n")

    def wallpaper_fitness_score(self, image_path: str) -> int | None:
        """Tiebreaker: if both tech and aesthetic are perfect, ask the model
        one more time whether this image truly works as a wallpaper.

        Returns a replacement aesthetic score (1-10), or None if skipped.
        """
        fitness_prompt = self._load_fitness_prompt()
        if not fitness_prompt:
            return None

        image_b64 = self._encode_image(image_path)
        logger.info("[fitness] Running wallpaper fitness tiebreaker...")

        try:
            thinking, raw = self._call_vision(fitness_prompt, image_b64)
        except Exception as exc:
            logger.error("[fitness] API call failed: %s", exc)
            return None

        self._log_thinking("fitness", thinking)
        self._log_raw("fitness", raw)

        parsed = self._extract_json(raw) if raw else None
        if parsed is None:
            logger.warning("[fitness] No valid JSON, skipping tiebreaker")
            return None

        deduction = float(parsed.get("deduction", 0))
        reason = parsed.get("reason", "")
        score = max(1, int((10.0 - deduction) // 1))
        logger.info("[fitness] Deduction: %s | Score: %s/10 | Reason: %s", deduction, score, reason)
        return score

    def _load_fitness_prompt(self) -> str | None:
        if not os.path.exists(self._fitness_prompt_path):
            logger.warning("Fitness prompt not found: %s", self._fitness_prompt_path)
            return None
        with open(self._fitness_prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    # ------------------------------------------------------------------
    # Dimension scoring
    # ------------------------------------------------------------------

    def _score_dimension(self, name: str, prompt: str, image_b64: str) -> DimensionResult:
        """Score a single dimension. Falls back to text-only recovery on failure."""
        logger.info("[%s] Evaluating...", name)

        thinking: str = ""
        raw: str = ""

        # -- primary vision call --
        try:
            thinking, raw = self._call_vision(prompt, image_b64)
        except Exception as exc:
            logger.error("[%s] API call failed: %s", name, exc)

        self._log_thinking(name, thinking)
        self._log_raw(name, raw)

        # -- parse --
        parsed = self._extract_json(raw) if raw else None

        if parsed is not None:
            deduction = float(parsed.get("deduction", 0))
            reason = parsed.get("reason", "")
            logger.info("[%s] Deduction: %s | Reason: %s", name, deduction, reason)
            return DimensionResult(name=name, reason=reason, deduction=deduction)

        # -- recovery path --
        logger.warning("[%s] Primary response invalid or missing. Attempting recovery...", name)
        recovered = self._attempt_recovery(name, thinking, raw)

        if recovered is not None:
            return DimensionResult(name=name, **recovered, recovered=True)

        # -- total failure --
        logger.error("[%s] Recovery also failed. Using safe default.", name)
        return DimensionResult(
            name=name,
            reason=f"[ERROR] Scoring failed. Thinking: {len(thinking)} chars, output: {len(raw)} chars.",
            deduction=0.0,
        )

    # ------------------------------------------------------------------
    # API calls
    # ------------------------------------------------------------------

    def _call_vision(self, system_prompt: str, image_b64: str) -> tuple[str, str]:
        """Send image + prompt to the vision model.

        Returns (thinking_text, raw_content).
        """
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                ]},
            ],
            temperature=0.0,
            max_tokens=self.max_tokens,
        )
        msg = resp.choices[0].message
        thinking = self._extract_thinking(msg)
        raw = msg.content.strip() if msg.content else ""
        return thinking, raw

    def _call_text(self, system_prompt: str, user_text: str) -> str:
        """Send a text-only prompt (no image). Used by recovery."""
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            temperature=0.0,
            max_tokens=self.max_tokens,
        )
        return resp.choices[0].message.content.strip() if resp.choices[0].message.content else ""

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    def _attempt_recovery(self, name: str, thinking: str, raw: str) -> dict | None:
        """Try to extract a score from truncated/malformed output by feeding
        the model's own thinking back without the image.

        Returns {"reason": str, "deduction": float} or None.
        """
        fallback_prompt = self._load_fallback_prompt()
        if not fallback_prompt:
            return None

        parts = []
        if thinking:
            parts.append(f"=== YOUR ORIGINAL THINKING ===\n{thinking.strip()}")
        if raw:
            parts.append(f"=== YOUR PARTIAL OUTPUT ===\n{raw.strip()}")
        if not parts:
            logger.warning("[%s] Recovery skipped: nothing to work from.", name)
            return None

        user_message = "\n\n".join(parts)
        logger.info("[%s] >>> Recovery: %d chars of context ...", name, len(user_message))

        try:
            recovery_text = self._call_text(fallback_prompt, user_message)
        except Exception as exc:
            logger.error("[%s] Recovery API call failed: %s", name, exc)
            return None

        if self.debug:
            logger.info("[%s] Recovery output:\n%s", name, recovery_text)
        else:
            logger.info("[%s] Recovery output: %d chars", name, len(recovery_text))

        parsed = self._extract_json(recovery_text)
        if parsed is None:
            logger.error("[%s] Recovery produced invalid JSON:\n%s", name, recovery_text)
            return None

        reason = parsed.get("reason", "")
        deduction = float(parsed.get("deduction", 0))
        logger.info("[%s] Recovery succeeded -> deduction: %s", name, deduction)
        return {"reason": reason, "deduction": deduction}

    def _load_fallback_prompt(self) -> str | None:
        if not os.path.exists(self._fallback_prompt_path):
            logger.warning("Fallback prompt not found: %s", self._fallback_prompt_path)
            return None
        with open(self._fallback_prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    # ------------------------------------------------------------------
    # Prompt loading
    # ------------------------------------------------------------------

    def _load_prompts(self) -> list[dict]:
        """Load .md files from prompts_dir, skipping reserved _prefixed files."""
        pattern = os.path.join(self.prompts_dir, "*.md")
        files = sorted(glob.glob(pattern))
        prompts = []
        for fpath in files:
            name = os.path.basename(fpath)
            if name.startswith("_"):
                continue
            with open(fpath, "r", encoding="utf-8") as f:
                prompts.append({"name": os.path.splitext(name)[0], "content": f.read()})
        if not prompts:
            raise FileNotFoundError(f"No scoring prompt files found in: {self.prompts_dir}")
        logger.info("Loaded %d prompt(s) from: %s", len(prompts), self.prompts_dir)
        return prompts

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _encode_image(image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    @staticmethod
    def _extract_thinking(message) -> str:
        """Extract reasoning/thinking content from a chat message.

        Checks standard SDK attribute first, then model_extra fallbacks.
        """
        thinking = getattr(message, "reasoning_content", None)
        if thinking:
            return thinking
        extra = getattr(message, "model_extra", {}) or {}
        for key in ("reasoning_content", "thinking", "reasoning"):
            if key in extra:
                return extra[key]
        return ""

    @staticmethod
    def _extract_json(text: str) -> dict | None:
        """Extract a JSON object from text that may contain markdown fences or
        surrounding prose."""
        cleaned = re.sub(r"```(?:json)?\s*", "", text).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        return None

    def _log_thinking(self, name: str, thinking: str):
        if not thinking:
            return
        if self.debug:
            logger.info("[%s] --- thinking (%d chars) ---", name, len(thinking))
            logger.info(thinking.strip())
            logger.info("[%s] --- end of thinking ---", name)
        else:
            logger.info("[%s] --- thinking captured (%d chars, use --debug to view) ---", name, len(thinking))

    def _log_raw(self, name: str, raw: str):
        if self.debug:
            logger.info("[%s] Raw output:\n%s", name, raw)
        else:
            preview = raw[:200]
            if len(raw) > 200:
                preview += f"... ({len(raw)} chars, use --debug to view)"
            logger.info("[%s] Raw output: %s", name, preview)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

# Aesthetic prompts directory (separate score category)
DEFAULT_AESTHETIC_PROMPTS_DIR = "prompts_aesthetic"
# Full-power mode directories
FULL_PROMPTS_DIR = "prompts_full"
FULL_AESTHETIC_PROMPTS_DIR = "prompts_aesthetic_full"


def _run_suite(image_path: str, prompts_dir: str, label: str, debug: bool,
               max_tokens: int | None = None) -> ScoreReport | None:
    """Run a scoring suite. Returns None if directory is missing or empty."""
    if not os.path.isdir(prompts_dir):
        logger.warning("%s suite skipped: directory not found (%s)", label, prompts_dir)
        return None
    try:
        scorer = WallpaperScorer(prompts_dir=prompts_dir, debug=debug, max_tokens=max_tokens)
        return scorer.score(image_path)
    except FileNotFoundError:
        logger.warning("%s suite skipped: no prompt files in %s", label, prompts_dir)
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Score a wallpaper across multiple dimensions using local AI."
    )
    parser.add_argument("-i", "--image", required=True, help="Path to image file")
    parser.add_argument(
        "-d", "--prompts-dir", default=WallpaperScorer.DEFAULT_PROMPTS_DIR,
        help="Directory for technical scoring prompts (default: prompts/)",
    )
    parser.add_argument(
        "--prompts-aesthetic-dir", default=DEFAULT_AESTHETIC_PROMPTS_DIR,
        help="Directory for aesthetic scoring prompts (default: prompts_aesthetic/)",
    )
    parser.add_argument(
        "-f", "--full", action="store_true",
        help="Full-power mode: remove token limits, use deep-thinking prompts",
    )
    parser.add_argument(
        "--debug", action="store_true", default=True,
        help="Show full thinking / raw output in log (default: on)",
    )
    parser.add_argument(
        "--no-debug", action="store_false", dest="debug",
        help="Suppress verbose output",
    )
    args = parser.parse_args()

    # Resolve directories and token limit based on mode
    if args.full:
        tech_dir = FULL_PROMPTS_DIR
        aesth_dir = FULL_AESTHETIC_PROMPTS_DIR
        max_tokens = -1
        logger.info("*** FULL POWER MODE enabled (max_tokens=-1, deep-thinking prompts) ***")
    else:
        tech_dir = args.prompts_dir
        aesth_dir = args.prompts_aesthetic_dir
        max_tokens = None  # use default 4096

    try:
        tech_report = _run_suite(args.image, tech_dir, "Technical", args.debug, max_tokens=max_tokens)
        aesth_report = _run_suite(args.image, aesth_dir, "Aesthetic", args.debug, max_tokens=max_tokens)

        if tech_report is None and aesth_report is None:
            print("Error: no scoring suites available.")
            return

        # --- Double-perfect tiebreaker: replace aesthetic score ---
        if (
            tech_report is not None and aesth_report is not None
            and tech_report.final_score == 10 and aesth_report.final_score == 10
        ):
            logger.info("Both scores are 10/10 — running wallpaper fitness tiebreaker...")
            fitness_dir = tech_dir  # use same prompt dir (normal or full)
            fitness_scorer = WallpaperScorer(prompts_dir=fitness_dir, debug=args.debug,
                                             max_tokens=max_tokens)
            fitness_score = fitness_scorer.wallpaper_fitness_score(args.image)
            if fitness_score is not None:
                aesth_report.final_score = fitness_score
                aesth_report.dimensions.append(DimensionResult(
                    name="fitness_tiebreaker",
                    reason=f"Double-perfect tiebreaker activated. Fitness score: {fitness_score}/10",
                    deduction=10.0 - fitness_score,
                ))

        # --- Combined output ---
        print(f"\n{'=' * 60}")
        print(f"File: {os.path.basename(args.image)}")
        print(f"{'=' * 60}")

        if tech_report:
            print(f"\n  ◆ TECHNICAL SCORE ◆")
            for d in tech_report.dimensions:
                tag = " [RECOVERED]" if d.recovered else ""
                print(f"    [{d.name}]{tag}  deduction: {d.deduction}")
                print(f"             reason: {d.reason}")
            print(f"  ─────────────────────────────")
            print(f"  Total deduction: {tech_report.total_deduction}")
            print(f"  Technical score: {tech_report.final_score}/10")

        if aesth_report:
            print(f"\n  ◆ AESTHETIC SCORE ◆")
            for d in aesth_report.dimensions:
                tag = " [RECOVERED]" if d.recovered else ""
                print(f"    [{d.name}]{tag}  deduction: {d.deduction}")
                print(f"             reason: {d.reason}")
            print(f"  ─────────────────────────────")
            print(f"  Total deduction: {aesth_report.total_deduction}")
            print(f"  Aesthetic score: {aesth_report.final_score}/10")

        print(f"\n{'=' * 60}")
        if tech_report:
            print(f"  Technical: {tech_report.final_score}/10", end="")
        if aesth_report:
            print(f"  |  Aesthetic: {aesth_report.final_score}/10", end="")
        print(f"\n{'=' * 60}\n")

    except KeyboardInterrupt:
        logger.info("Interrupted by user (Ctrl+C).")
        print("\nInterrupted.")
    except Exception as e:
        logger.error("Scoring failed: %s", e)
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
