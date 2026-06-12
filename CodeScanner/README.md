# 代码安全问题 AI 扫描器

结合 Python 脚本和 AI CLI 工具（ClaudeCode / OpenCode / Codex），对代码工程逐目录进行安全漏洞扫描。通过分割子模块、限定 AI 工作目录的方式避免大模型上下文溢出导致的漏报和误报。

## 项目结构

```
D:\CodeScanner\
├── main.py            # 入口、参数解析、日志、目录遍历、Prompt 加载、结果落盘、流程编排
├── ai_client.py       # AI 客户端抽象层（ClaudeCode / OpenCode / Codex）
├── Prompts/           # Prompt 模板
│   ├── V1/            #   Skill 模式（9 类）
│   └── V2/            #   Agent 模式
├── TestCases/         # 测试用例
├── output/            # 扫描结果输出（运行时生成）
└── PLAN_AGENT_MIGRATION.md  # Agent 迁移设计文档
```

## 使用方法

```bash
python main.py \
  --code-root <目标代码根路径> \
  --ai-tool <claudecode|opencode> \
  --prompt-template <Prompt 模板文件路径> \
  [--split-granularity single-folder] \
  [--debug]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `--code-root` | 是 | 代码工程根目录 |
| `--ai-tool` | 是 | AI 工具选择：`claudecode`、`opencode`、`codex`（均已支持） |
| `--prompt-template` | 是 | Prompt 模板文件路径（UTF-8） |
| `--split-granularity` | 否 | 代码分割细粒度，默认 `single-folder`（仅支持此值） |
| `--debug` | 否 | 开启后 `scanner.log` 记录 DEBUG 级别详情（CLI 命令、Prompt 内容、AI 对话原文等），关闭时仅记录 INFO 级别扫描进度 |

### Prompt 模板

提供两种模式：

**V1 — Skill 模式**（`Prompts/V1/`，通过 `/skill-name` 调用）：
- `HardcodedPasswordPrompt.md` — 调用 `/hardcoded-secret-scan-v3`
- 其余 8 类扫描类推（Account / Crypto / Port / Protocol / Cert / URL / Random / SensitivePrint）

**V2 — Agent 模式**（`Prompts/V2/`，通过自定义 Agent Profile 扫描，推荐）：
- `HardcodedPasswordPromptV2.md` — 调用全局 Agent `~/.claude/agents/hardcoded-secret-agent.md`
- Agent 模式优势：规则与流程解耦、独立上下文不占主会话、模型自动跟随主会话配置
- **前置条件**：需先将 Agent Profile 部署到 `~/.claude/agents/`。可使用 `security-skill-to-agent` skill 从 V3 Skill 自动生成
- 其余 8 类 V2 Prompt 按需生成

Prompt 中应明确：
1. 约束 AI 仅扫描当前工作目录，避免访问子文件夹
2. 要求 AI 将结果写入固定文件 `AI测试结果.md`（程序以此读取结果）

示例 (`Prompts/V1/HardcodedPasswordPrompt.md`)：

```
本次任务将扫描代码中所有的密码秘钥硬编码情景。
1. 请仅仅测试当前目录下的所有文件，不包含子文件夹。
2. 测试结束以后，将结果完整总结，滤掉测试过程信息，
   在根目录生成 "AI测试结果.md"。后续会使用脚本读取，文件名必须一致。
```

> 注意：Prompt 中可通过 `/skill-name` 引用已配置的 Claude Code skill，AI 会自动调用该 skill 的子代理机制。

## 执行流程

1. 读取并解析 Prompt 模板
2. 递归遍历代码根目录（深度优先），过滤业界标准非代码目录
3. 遍历每个子目录，先清理该目录下残留的 `AI测试结果.md`（如有），再调用 AI CLI 进行单次安全扫描
4. AI 在子目录下生成 `AI测试结果.md`，程序读取该文件作为扫描结果
5. 每个目录扫描完成后：
   - 单独结果落盘至 `output/mirrored/<相对路径>/<目录名>.md`
   - 追加结果至 `output/combined_results.md`
6. 所有目录扫描完毕后退出；中途单个目录失败（超时/未生成结果文件）记录错误后继续扫描后续目录

## 目录过滤规则

遍历时自动跳过以下行业标准非代码目录：

| 类别 | 忽略目录 |
|------|---------|
| 版本控制 | `.git`, `.svn`, `.hg` |
| 依赖 | `node_modules`, `vendor`, `Pods`, `.venv`, `venv`, `env` |
| Python 缓存 | `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.tox`, `.nox`, `.ruff_cache`, `.eggs` |
| 构建产物 | `dist`, `build`, `target`, `out`, `bin`, `obj`, `.next`, `.nuxt`, `.output` |
| IDE | `.idea`, `.vscode`, `.vs`, `.fleet`, `.settings` |
| 缓存/覆盖率 | `.cache`, `.turbo`, `.parcel-cache`, `coverage`, `.nyc_output`, `htmlcov` |

## 输出结构

```
output/
├── mirrored/                    # 镜像原始工程目录结构
│   └── src/
│       └── auth/
│           ├── auth.md          # src/auth/ 的扫描结果
│           └── handlers/
│               └── handlers.md  # src/auth/handlers/ 的扫描结果
└── combined_results.md          # 所有结果汇总（Markdown 追加格式）
```

## 自测

### V2 Agent 模式（推荐）

```bash
python main.py --code-root D:\CodeScanner\TestCases --ai-tool claudecode --prompt-template D:\CodeScanner\Prompts\V2\HardcodedPasswordPromptV2.md --debug
```

### V1 Skill 模式

```bash
# 使用 ClaudeCode
python main.py --code-root D:\CodeScanner\TestCases --ai-tool claudecode --prompt-template D:\CodeScanner\Prompts\V1\HardcodedPasswordPrompt.md --debug

# 使用 OpenCode
python main.py --code-root D:\CodeScanner\TestCases --ai-tool opencode --prompt-template D:\CodeScanner\Prompts\V1\HardcodedPasswordPrompt.md --debug

# 使用 Codex
python main.py --code-root D:\CodeScanner\TestCases --ai-tool codex --prompt-template D:\CodeScanner\Prompts\V1\HardcodedPasswordPrompt.md --debug
```

`TestCases/` 下预埋了包含安全漏洞的示例代码：
- `module_a/db.py` — SQL 注入、明文密码、资源泄漏
- `module_a/config.py` — 硬编码凭据、命令注入
- `module_b/web.js` — 反射型 XSS
- `module_b/file_handler.py` — 路径遍历

## 注意事项

- 需要预先安装所选 AI 工具的 CLI 并确保在 PATH 中可用
- **Agent 模式（V2）**：需将 Agent Profile 部署到 `~/.claude/agents/` 目录（全局位置），否则扫描外部工程时无法被发现。可使用 `security-skill-to-agent` skill 从 V3 Skill 自动生成
- AI 调用为阻塞串行模式，大工程耗时较长，建议后台运行
- 日志双通道：控制台始终输出扫描进度；`scanner.log` 默认记录 INFO 级别信息（进度、退出码、耗时），加 `--debug` 后额外记录 CLI 命令、Prompt 内容及 AI 对话原文
- AI 调用默认超时 1000s（Codex 1500s），max_turns 默认 50；超时或缺结果文件时记录错误并跳过当前目录，继续扫描后续目录
- 扫描结束会汇总成功/失败数量；CLI 未找到仍会立即终止（无法继续）
