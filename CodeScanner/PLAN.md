# 代码安全问题AI扫描器 — 实现计划

## 1. 项目结构

```
D:\CodeScanner\
├── main.py            # 入口、参数解析、日志、目录遍历、Prompt加载、结果落盘、流程编排
├── ai_client.py       # AI 客户端抽象层（基类 + ClaudeCode/OpenCode 实现 + 工厂函数）
└── output/            # 扫描结果输出（运行时生成）
```

---

## 2. AI 工具 CLI 参数调研

### 2.1 ClaudeCode CLI (非交互单次模式)

核心用法：`-p` / `--print` 进入 headless 模式，单次交互后退出，结果输出到 stdout。

| 关键参数 | 说明 |
|----------|------|
| `-p`, `--print` | **必用** — 非交互单次模式，执行 prompt 后打印结果并退出 |
| `--output-format text` | 输出纯文本（默认）。headless 模式下**不含 thinking 过程**，仅返回最终响应，满足需求 |
| `--output-format json` | 输出 JSON 流，可区分 `type: "assistant"` 和 `type: "thinking"` |
| `--max-turns <N>` | 限制 agent 执行轮数（headless 默认约 10 轮） |
| `--permission-mode bypassPermissions` | 跳过权限确认（CI/自动化场景需要） |
| `--model <model>` | 指定模型 |

**结论 — 我们将使用的命令：**
```bash
claude -p "<prompt>" --output-format text --max-turns 15 --permission-mode bypassPermissions
```
- 工作目录通过 `subprocess.run(cwd=workdir)` 设定（ClaudeCode 使用当前进程的 working directory）
- `--output-format text` 直接返回不含 thinking 的最终结果
- 备选：`--output-format json` → 解析 JSON 行，只收集 `type == "assistant"` 的片段（当需要更精确控制时使用）

### 2.2 OpenCode CLI (非交互单次模式)

核心用法：`opencode run` 子命令，不启动 TUI，直接执行 prompt。

| 关键参数 | 说明 |
|----------|------|
| `opencode run "<prompt>"` | **必用** — 非交互单次执行 |
| `--format default` | 默认文本输出（备用） |
| `--format json` | 结构化 JSON 输出 |
| `-m`, `--model` | 指定模型，格式 `provider/model-name` |
| `-f`, `--file` | 附加文件到消息中（可重复） |
| `--dangerously-skip-permissions` | 自动批准所有权限 |

**结论 — 我们将使用的命令（占位）：**
```bash
opencode run "<prompt>" --format default --dangerously-skip-permissions
```

---

## 3. main.py 设计

### 3.1 整体结构

```
main.py
├── setup_logging()              # 日志双通道配置
├── parse_args()                 # argparse 参数解析与校验
├── load_prompt(path) -> str     # 读取模板 + CLI 字符转义
├── collect_dirs(root) -> list   # 递归收集子目录（深度优先 + 行业标准过滤）
├── save_single_result(...)      # 镜像目录写入
├── append_combined_result(...)  # 汇总文件追加
└── main()                       # 流程编排
```

### 3.2 参数解析 `parse_args()`

| 参数 | 必填 | 说明 |
|------|------|------|
| `--code-root` | 是 | 代码根路径，校验路径存在且为目录 |
| `--ai-tool` | 是 | 固定 `choices=["claudecode", "opencode"]` |
| `--prompt-template` | 是 | Prompt 模板文件路径，校验文件存在 |
| `--split-granularity` | 否 | 默认 `"single-folder"`，当前仅支持此值 |

校验失败 → `sys.exit(1)`。

### 3.3 Prompt 加载 `load_prompt(path)`

- 读取文件内容（UTF-8）
- CLI 安全转义：
  - 双引号 `"` → `\"`
  - 反斜杠 `\` → `\\`
  - 移除不可见控制字符（保留常见空白字符）
- 返回处理后的字符串

### 3.4 目录遍历 `collect_dirs(root)`

#### 过滤策略（行业标准）

参照业界主流代码扫描工具（ESLint、Oxlint、Semgrep、SonarQube）的默认忽略规则：

| 类别 | 忽略目录 |
|------|---------|
| 版本控制 | `.git`, `.svn`, `.hg` |
| 依赖目录 | `node_modules`, `vendor`, `Pods`, `.venv`, `venv`, `env` |
| Python 缓存 | `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.tox`, `.nox`, `.ruff_cache`, `.eggs`, `*.egg-info` |
| 构建产物 | `dist`, `build`, `target`, `out`, `bin`, `obj`, `.next`, `.nuxt`, `.output` |
| IDE 配置 | `.idea`, `.vscode`, `.vs`, `.fleet`, `.settings` |
| 缓存目录 | `.cache`, `.turbo`, `.parcel-cache` |
| 覆盖率 | `coverage`, `.nyc_output`, `htmlcov` |
| OS 文件 | `.DS_Store`, `Thumbs.db` |

**实现方式：**
- 硬编码 `IGNORE_DIRS` 集合
- 使用 `os.walk()` 遍历时原地修改 `dirnames[:]` 剔除忽略目录（不清除 `.gitignore` 未追踪的那部分，因为代码工程本身就在仓库内）
- 遍历顺序：深度优先（`os.walk()` 默认），与 README 示例 `[A, A/B, A/C, A/B/D]` 一致
- **根目录本身作为第一个扫描单元**（已确认）
- 输出：`list[Path]`

### 3.5 结果落盘

**`save_single_result(result, workdir, code_root, output_base)`**
- 计算 `relative = workdir.relative_to(code_root)`
- 写入 `output_base/mirrored/<relative>/<workdir.name>.md`
- 自动创建父目录

**`append_combined_result(result, workdir, code_root, combined_file)`**
- 追加格式（Markdown）：
  ```markdown
  ============================================================
  ## Scan Result for: <相对路径>
  **Scan Time:** <ISO 时间戳>
  ============================================================
  <AI 返回原始内容>
  ```
- 追加模式写入 `output/combined_results.md`

### 3.6 日志 `setup_logging()`

- 控制台：`INFO` 级别，显示扫描进度
- 文件 `scanner.log`：`DEBUG` 级别，记录完整 CLI 命令、stdout/stderr、返回码、耗时
- 格式：`[时间] [级别] 消息`

示例：
```
[12:30:01] INFO  CodeScanner 启动
[12:30:01] INFO  代码根路径: D:\MyProject
[12:30:01] INFO  AI 工具: claudecode
[12:30:01] INFO  发现 15 个子目录待扫描
[12:30:02] INFO  [1/15] 扫描中: .
[12:35:12] INFO  [1/15] 完成 (耗时 310s)
[12:35:12] INFO  [2/15] 扫描中: src\auth
...
[12:45:00] INFO  全部扫描完成，结果保存在 D:\CodeScanner\output\
```

### 3.7 主流程 `main()`

```python
def main():
    args = parse_args()
    setup_logging()

    prompt = load_prompt(args.prompt_template)
    dirs = collect_dirs(args.code_root)

    client = get_client(args.ai_tool)

    output_base = Path("output")
    combined_file = output_base / "combined_results.md"
    combined_file.parent.mkdir(parents=True, exist_ok=True)

    total = len(dirs)
    for i, workdir in enumerate(dirs, start=1):
        logger.info(f"[{i}/{total}] 扫描中: {workdir.relative_to(args.code_root)}")
        t0 = time.time()

        try:
            result = client.invoke(prompt, workdir)
        except AICallError as e:
            logger.error(f"AI 调用失败 [{workdir}]: {e}")
            sys.exit(1)

        elapsed = time.time() - t0
        logger.info(f"[{i}/{total}] 完成 (耗时 {elapsed:.0f}s)")

        save_single_result(result, workdir, args.code_root, output_base)
        append_combined_result(result, workdir, args.code_root, combined_file)

    logger.info(f"全部扫描完成，共 {total} 个目录，结果保存在 {output_base.absolute()}")
```

---

## 4. ai_client.py 设计

### 4.1 结构

```
ai_client.py
├── class AICallError(Exception)     # 自定义异常
├── class AIClient(ABC)              # 抽象基类
│   └── invoke(prompt, workdir) -> str
├── class ClaudeCodeClient(AIClient) # ClaudeCode CLI 实现
├── class OpenCodeClient(AIClient)   # OpenCode CLI 实现（占位）
└── get_client(name) -> AIClient     # 工厂函数
```

### 4.2 `AIClient.invoke(prompt, workdir) -> str`

- 输入：处理后的 prompt 字符串 + 工作目录 Path
- 输出：AI 最终响应文本（不含 thinking）
- 内部：`subprocess.run()` 阻塞等待，捕获 stdout
- 返回码非 0 或超时 → 抛出 `AICallError`
- `platform.system()` 判断 OS 构造命令

### 4.3 ClaudeCodeClient

```bash
# 命令模板
claude -p "<prompt>" --output-format text --max-turns 15 --permission-mode bypassPermissions
```
- 工作目录通过 `subprocess.run(cwd=workdir)` 设定
- `--output-format text` 直接返回不含 thinking 的最终结果（已验证：headless 模式下 text 输出仅包含 assistant 响应）
- 超时：3600s
- Windows 上使用 `powershell -Command "& claude ..."` 以避免 cmd 引号转义问题

### 4.4 OpenCodeClient

```bash
# 命令模板（占位）
opencode run "<prompt>" --format default
```
- 暂抛出 `NotImplementedError`，待后续实现

### 4.5 工厂函数

```python
def get_client(name: str) -> AIClient:
    if name == "claudecode":
        return ClaudeCodeClient()
    if name == "opencode":
        return OpenCodeClient()
    raise ValueError(f"Unsupported AI tool: {name}")
```

---

## 5. 异常处理

| 异常场景 | 处理方式 |
|---------|---------|
| 参数校验失败 | 打印错误 + `sys.exit(1)` |
| Prompt 文件不存在/无法读取 | 打印错误 + `sys.exit(1)` |
| 代码根路径不存在/无权限 | 打印错误 + `sys.exit(1)` |
| AI CLI 调用超时 | 打印子文件夹路径 + `sys.exit(1)` |
| AI CLI 返回非 0 | 打印 stderr + `sys.exit(1)` |
| 结果落盘写失败 | 打印错误 + `sys.exit(1)` |
| 用户 Ctrl+C | 捕获 `KeyboardInterrupt`，打印"用户中断"后退出 |

> 原则：AI 调用失败立即终止，不继续后续扫描。

---

## 6. 输出目录结构

```
output/
├── mirrored/
│   ├── .md                     # 根目录扫描结果（workdir.name = "."，用点号命名）
│   └── src/
│       └── auth/
│           ├── auth.md         # 扫描 src/auth/ 的结果
│           └── handlers/
│               └── handlers.md # 扫描 src/auth/handlers/ 的结果
└── combined_results.md         # 所有结果汇总
```

> 根目录的单独结果文件命名为 `.md`（因为 `Path(".").name` 返回 `"."`），改为特殊处理：根目录结果文件命名为 `_root_.md`。

---

## 7. 已确认事项

1. **扫描根目录**：是，根目录作为第一个扫描单元
2. **结果文件格式**：`.md`（Markdown）
3. **并发**：串行
4. **目录过滤**：行业标准黑名单 + `os.walk()` 原地剪枝
5. **ClaudeCode 调用方式**：`claude -p "<prompt>" --output-format text --max-turns 15 --permission-mode bypassPermissions`
6. **OpenCode 调用方式**：`opencode run "<prompt>" --format default`（占位，待后续实现确认）

---

## 8. 实现顺序

1. `ai_client.py` — 无依赖，先完成
2. `main.py` — 依赖 `ai_client.py`，完成后即可端到端测试
