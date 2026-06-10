"""AI 客户端抽象层：支持 ClaudeCode、OpenCode、Codex 三种 CLI 工具。"""

import logging
import os
import re
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger("CodeScanner")

# 匹配 ANSI 转义序列
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _find_cli(*names: str) -> str:
    """查找可执行文件路径。

    查找顺序：先找 names 列表中的各项，若找到的是 .cmd 则读取其内容
    解析出实际 .exe 路径（绕过 cmd.exe 的 %* 换行截断问题）。
    """
    for name in names:
        path = shutil.which(name)
        if path is None:
            continue
        # 如果是 .cmd 脚本，解析出实际的 .exe 路径
        if path.lower().endswith(".cmd"):
            exe = _parse_cmd_launcher(path)
            if exe:
                logger.debug("从 %s 解析出实际可执行文件: %s", path, exe)
                return exe
        return path
    raise AICallError(f"未找到 {' 或 '.join(names)} 命令，请确认 CLI 已安装并在 PATH 中")


def _parse_cmd_launcher(cmd_path: str) -> str | None:
    """解析 npm 全局安装的 .cmd 启动器，返回实际 .exe 路径。"""
    try:
        with open(cmd_path, "r", encoding="utf-8") as f:
            content = f.read()
        # 匹配: "%dp0%\node_modules\...\bin\xxx.exe"   %*
        import re as _re
        m = _re.search(r'"%dp0%\\(.+?\.exe)"', content)
        if m:
            cmd_dir = Path(cmd_path).parent
            exe_path = cmd_dir / m.group(1)
            if exe_path.is_file():
                return str(exe_path)
    except Exception:
        pass
    return None


def _strip_ansi(text: str) -> str:
    """移除字符串中的 ANSI 转义序列。"""
    return _ANSI_RE.sub("", text)


def _find_codex() -> list[str]:
    """解析 codex CLI 为直接 node 调用，绕过 .cmd 包装器的引号截断问题。

    codex.cmd 通过 `%*` 将参数转发给 node，但 cmd.exe 对多行文本和
    嵌入双引号的处理会导致 prompt 被截断。直接调用 node + codex.js
    可让 subprocess 通过 CreateProcess 传递参数，避免 shell 介入。
    """
    import os as _os
    npm_dir = Path(_os.environ.get("APPDATA", "")) / "npm"
    codex_js = npm_dir / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"

    node = shutil.which("node") or shutil.which("node.exe")
    if node is None:
        raise AICallError("未找到 node 命令，请确认 Node.js 已安装并在 PATH 中")

    if not codex_js.is_file():
        raise AICallError(f"未找到 codex.js: {codex_js}，请确认 codex CLI 已安装")

    logger.debug("Codex 解析: node=%s, script=%s", node, codex_js)
    return [node, str(codex_js)]


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

    def __init__(self, max_turns: int = 15, timeout: int = 1000):
        self.max_turns = max_turns
        self.timeout = timeout

    def invoke(self, prompt: str, workdir: Path) -> str:
        cli = _find_cli("claude", "claude.cmd")
        cmd = [
            cli,
            "-p", prompt,
            "--output-format", "text",
            "--max-turns", str(self.max_turns),
            "--permission-mode", "bypassPermissions",
        ]

        logger.debug("CLI 命令: %s", " ".join(f'"{c}"' if " " in c else c for c in cmd))
        logger.info("工作目录: %s", workdir)

        process = subprocess.Popen(
            cmd,
            cwd=str(workdir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = process.communicate(timeout=self.timeout)
            returncode = process.returncode
            logger.info("退出码: %d", returncode)
            logger.info("stdout 长度: %d 字节", len(stdout_bytes or b""))
        except subprocess.TimeoutExpired:
            process.kill()
            stdout_bytes, stderr_bytes = process.communicate()
            raise AICallError(f"ClaudeCode 调用超时（{self.timeout}s）: {workdir}")

        if returncode != 0:
            stderr = stderr_bytes.decode("utf-8", errors="replace").strip() if stderr_bytes else ""
            stdout = stdout_bytes.decode("utf-8", errors="replace").strip() if stdout_bytes else ""
            detail = f"stderr: {stderr}" if stderr else f"stdout: {stdout}" if stdout else "(无输出)"
            raise AICallError(
                f"ClaudeCode 返回非零退出码 ({returncode}) at {workdir}: {detail}"
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace").strip() if stdout_bytes else ""
        return stdout


class OpenCodeClient(AIClient):
    """通过 OpenCode CLI (`opencode run`) 进行非交互单次调用。"""

    def __init__(self, timeout: int = 1000):
        self.timeout = timeout

    def invoke(self, prompt: str, workdir: Path) -> str:
        cli = _find_cli("opencode", "opencode.cmd")
        cmd = [
            cli,
            "run", prompt,
            "--dir", str(workdir),
            "--format", "default",
            "--dangerously-skip-permissions",
        ]

        logger.debug("CLI 命令: %s", " ".join(f'"{c}"' if " " in c else c for c in cmd))
        logger.info("工作目录: %s", workdir)

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = process.communicate(timeout=self.timeout)
            returncode = process.returncode
            logger.info("退出码: %d", returncode)
            logger.info("stdout 长度: %d 字节", len(stdout_bytes or b""))
        except subprocess.TimeoutExpired:
            process.kill()
            stdout_bytes, stderr_bytes = process.communicate()
            raise AICallError(f"OpenCode 调用超时（{self.timeout}s）: {workdir}")

        if returncode != 0:
            stderr = stderr_bytes.decode("utf-8", errors="replace").strip() if stderr_bytes else ""
            stdout = stdout_bytes.decode("utf-8", errors="replace").strip() if stdout_bytes else ""
            detail = f"stderr: {stderr}" if stderr else f"stdout: {stdout}" if stdout else "(无输出)"
            raise AICallError(
                f"OpenCode 返回非零退出码 ({returncode}) at {workdir}: {detail}"
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace").strip() if stdout_bytes else ""
        return _strip_ansi(stdout)


class CodexClient(AIClient):
    """通过 OpenAI Codex CLI (`codex exec`) 进行非交互单次调用。"""

    def __init__(self, timeout: int = 1500):
        self.timeout = timeout

    def invoke(self, prompt: str, workdir: Path) -> str:
        cli_prefix = _find_codex()
        cmd = [
            *cli_prefix,
            "exec",
            "--cd", str(workdir),
            "--sandbox", "danger-full-access",
            "--skip-git-repo-check",
            prompt,
        ]

        logger.debug("CLI 命令: %s", " ".join(f'"{c}"' if " " in c else c for c in cmd))
        logger.info("工作目录: %s", workdir)

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = process.communicate(timeout=self.timeout)
            returncode = process.returncode
            logger.info("退出码: %d", returncode)
            logger.info("stdout 长度: %d 字节", len(stdout_bytes or b""))
        except subprocess.TimeoutExpired:
            process.kill()
            stdout_bytes, stderr_bytes = process.communicate()
            raise AICallError(f"Codex 调用超时（{self.timeout}s）: {workdir}")

        if returncode != 0:
            stderr = stderr_bytes.decode("utf-8", errors="replace").strip() if stderr_bytes else ""
            stdout = stdout_bytes.decode("utf-8", errors="replace").strip() if stdout_bytes else ""
            detail = f"stderr: {stderr}" if stderr else f"stdout: {stdout}" if stdout else "(无输出)"
            raise AICallError(
                f"Codex 返回非零退出码 ({returncode}) at {workdir}: {detail}"
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace").strip() if stdout_bytes else ""
        return _strip_ansi(stdout)


def get_client(name: str) -> AIClient:
    """工厂函数：根据名称返回对应的 AI 客户端实例。"""
    if name == "claudecode":
        return ClaudeCodeClient()
    if name == "opencode":
        return OpenCodeClient()
    if name == "codex":
        return CodexClient()
    raise ValueError(f"不支持的 AI 工具: {name}")
