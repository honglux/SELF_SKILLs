"""代码安全问题 AI 扫描器 — 主入口。

遍历代码工程子目录，逐目录调用 AI 进行安全扫描，结果双份落盘。
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from ai_client import AICallError, get_client

logger = logging.getLogger("CodeScanner")

# ── 目录过滤（行业标准） ──────────────────────────────────────────────

IGNORE_DIRS = {
    # 版本控制
    ".git", ".svn", ".hg",
    # 依赖目录
    "node_modules", "vendor", "Pods", ".venv", "venv", "env",
    # Python 缓存 / 构建
    "__pycache__", ".pytest_cache", ".mypy_cache", ".tox", ".nox",
    ".ruff_cache", ".eggs",
    # 构建产物
    "dist", "build", "target", "out", "bin", "obj", ".next", ".nuxt", ".output",
    # IDE 配置
    ".idea", ".vscode", ".vs", ".fleet", ".settings",
    # 缓存
    ".cache", ".turbo", ".parcel-cache",
    # 覆盖率
    "coverage", ".nyc_output", "htmlcov",
}


# ── 日志系统 ──────────────────────────────────────────────────────────

def setup_logging():
    logger.setLevel(logging.DEBUG)

    # 控制台：INFO 级别
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)-5s %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(ch)

    # 文件：DEBUG 级别
    fh = logging.FileHandler("scanner.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)-5s %(message)s"))
    logger.addHandler(fh)


# ── 参数解析 ──────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="代码安全问题 AI 扫描器")
    parser.add_argument("--code-root", required=True, help="代码工程根目录")
    parser.add_argument("--ai-tool", required=True, choices=["claudecode", "opencode"], help="AI 工具选择")
    parser.add_argument("--prompt-template", required=True, help="Prompt 模板文件路径")
    parser.add_argument("--split-granularity", default="single-folder",
                        choices=["single-folder"], help="代码分割细粒度（默认 single-folder）")
    args = parser.parse_args()

    code_root = Path(args.code_root)
    if not code_root.is_dir():
        parser.error(f"代码根路径不存在或不是目录: {code_root}")

    prompt_path = Path(args.prompt_template)
    if not prompt_path.is_file():
        parser.error(f"Prompt 模板文件不存在: {prompt_path}")

    return args


# ── Prompt 加载 ───────────────────────────────────────────────────────

def load_prompt(path: str) -> str:
    """读取 Prompt 模板文件并移除控制字符。"""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    # 移除 ASCII 控制字符，保留常见空白（\n, \r, \t）
    return "".join(ch for ch in text if ch.isprintable() or ch in "\n\r\t")


# ── 目录遍历 ──────────────────────────────────────────────────────────

def collect_dirs(root: Path) -> list[Path]:
    """深度优先收集扫描目录，根目录排最前，忽略 IGNORE_DIRS 中的目录。"""
    dirs = [root]
    for dirpath_str, dirnames, _ in os.walk(str(root), topdown=True):
        dirnames[:] = sorted(
            d for d in dirnames if d not in IGNORE_DIRS
        )
        for d in dirnames:
            dirs.append(Path(dirpath_str) / d)
    return dirs


# ── 结果落盘 ──────────────────────────────────────────────────────────

def save_single_result(result: str, workdir: Path, code_root: Path, output_base: Path):
    """镜像目录结构写入单份结果。"""
    relative = workdir.resolve().relative_to(code_root.resolve())
    out_path = output_base / "mirrored" / relative / f"{workdir.name}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result, encoding="utf-8")


def append_combined_result(result: str, workdir: Path, code_root: Path, combined_file: Path):
    """追加到汇总结果文件。"""
    relative = workdir.resolve().relative_to(code_root.resolve())
    timestamp = datetime.now(timezone.utc).isoformat()
    header = (
        f"\n{'=' * 60}\n"
        f"## Scan Result for: {relative}\n"
        f"**Scan Time:** {timestamp}\n"
        f"{'=' * 60}\n\n"
    )
    with open(combined_file, "a", encoding="utf-8") as f:
        f.write(header)
        f.write(result)
        f.write("\n")


# ── 主流程 ────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    setup_logging()

    code_root = Path(args.code_root).resolve()
    logger.info("CodeScanner 启动")
    logger.info("代码根路径: %s", code_root)
    logger.info("AI 工具: %s", args.ai_tool)

    prompt = load_prompt(args.prompt_template)
    logger.debug("Prompt 长度: %d 字符", len(prompt))

    dirs = collect_dirs(code_root)
    logger.info("发现 %d 个子目录待扫描", len(dirs))

    client = get_client(args.ai_tool)

    output_base = Path("output")
    combined_file = output_base / "combined_results.md"
    combined_file.parent.mkdir(parents=True, exist_ok=True)

    total = len(dirs)
    for i, workdir in enumerate(dirs, start=1):
        rel_path = str(workdir.relative_to(code_root)) if workdir != code_root else "."
        logger.info("[%d/%d] 扫描中: %s", i, total, rel_path)
        t0 = time.time()

        try:
            result = client.invoke(prompt, workdir)
        except AICallError as e:
            logger.error("AI 调用失败 [%s]: %s", rel_path, e)
            sys.exit(1)

        elapsed = time.time() - t0
        logger.info("[%d/%d] 完成 (耗时 %.0fs)", i, total, elapsed)

        save_single_result(result, workdir, code_root, output_base)
        append_combined_result(result, workdir, code_root, combined_file)

    logger.info("全部扫描完成，共 %d 个目录，结果保存在 %s", total, output_base.resolve())


if __name__ == "__main__":
    main()
