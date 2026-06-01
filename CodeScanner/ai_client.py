"""AI 客户端抽象层：支持 ClaudeCode 和 OpenCode 两种 CLI 工具。"""

import logging
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger("CodeScanner")


class AICallError(Exception):
    """AI CLI 调用失败时抛出。"""
    pass


class AIClient(ABC):
    """AI 客户端抽象基类。"""

    @abstractmethod
    def invoke(self, prompt: str, workdir: Path) -> str:
        """阻塞调用 AI，返回完整响应文本。失败时抛出 AICallError。"""
        ...


class ClaudeCodeClient(AIClient):
    """通过 ClaudeCode CLI (`claude -p`) 进行非交互单次调用。"""

    def __init__(self, max_turns: int = 15, timeout: int = 3600):
        self.max_turns = max_turns
        self.timeout = timeout

    @staticmethod
    def _find_cli() -> str:
        """查找 claude 可执行文件路径。找不到则抛出 AICallError。"""
        for name in ["claude", "claude.cmd"]:
            path = shutil.which(name)
            if path:
                return path
        raise AICallError("未找到 claude 命令，请确认 ClaudeCode CLI 已安装并在 PATH 中")

    def invoke(self, prompt: str, workdir: Path) -> str:
        cli = self._find_cli()
        cmd = [
            cli,
            "-p", prompt,
            "--output-format", "text",
            "--max-turns", str(self.max_turns),
            "--permission-mode", "bypassPermissions",
        ]

        try:
            logger.debug("CLI 命令: %s", " ".join(f'"{c}"' if " " in c else c for c in cmd))
            logger.debug("工作目录: %s", workdir)

            result = subprocess.run(
                cmd,
                cwd=str(workdir),
                capture_output=True,
                timeout=self.timeout,
            )

            logger.debug("退出码: %d", result.returncode)
            logger.debug("stdout 长度: %d 字节", len(result.stdout or b""))
        except subprocess.TimeoutExpired:
            raise AICallError(f"ClaudeCode 调用超时（{self.timeout}s）: {workdir}")

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip() if result.stderr else ""
            raise AICallError(
                f"ClaudeCode 返回非零退出码 ({result.returncode}) at {workdir}: {stderr}"
            )

        stdout = result.stdout.decode("utf-8", errors="replace").strip() if result.stdout else ""
        return stdout


class OpenCodeClient(AIClient):
    """通过 OpenCode CLI (`opencode run`) 进行非交互单次调用。"""

    def invoke(self, prompt: str, workdir: Path) -> str:
        raise NotImplementedError("OpenCode CLI 支持尚未实现")


def get_client(name: str) -> AIClient:
    """工厂函数：根据名称返回对应的 AI 客户端实例。"""
    if name == "claudecode":
        return ClaudeCodeClient()
    if name == "opencode":
        return OpenCodeClient()
    raise ValueError(f"不支持的 AI 工具: {name}")
