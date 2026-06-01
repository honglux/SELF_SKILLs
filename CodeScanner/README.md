# 代码安全问题 AI 扫描器

结合 Python 脚本和 AI CLI 工具（ClaudeCode / OpenCode），对代码工程逐目录进行安全漏洞扫描。通过分割子模块、限定 AI 工作目录的方式避免大模型上下文溢出导致的漏报和误报。

## 项目结构

```
D:\CodeScanner\
├── main.py            # 入口、参数解析、日志、目录遍历、Prompt 加载、结果落盘、流程编排
├── ai_client.py       # AI 客户端抽象层（ClaudeCode / OpenCode）
├── TestCases/         # 测试用例
└── output/            # 扫描结果输出（运行时生成）
```

## 使用方法

```bash
python main.py \
  --code-root <目标代码根路径> \
  --ai-tool <claudecode|opencode> \
  --prompt-template <Prompt 模板文件路径> \
  [--split-granularity single-folder]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `--code-root` | 是 | 代码工程根目录 |
| `--ai-tool` | 是 | AI 工具选择，当前支持 `claudecode`（`opencode` 占位） |
| `--prompt-template` | 是 | Prompt 模板文件路径（UTF-8） |
| `--split-granularity` | 否 | 代码分割细粒度，默认 `single-folder`（仅支持此值） |

### Prompt 模板建议

Prompt 中应明确约束 AI 仅扫描当前工作目录，避免访问子文件夹。示例：

```
请确认当前文件夹下的所有文件的安全问题，请注意：**不要去访问子文件夹，仅仅测试当前文件夹下的所有文件。**
```

## 执行流程

1. 读取并解析 Prompt 模板
2. 递归遍历代码根目录（深度优先），过滤业界标准非代码目录
3. 遍历每个子目录，调用 AI CLI 以该目录为工作路径进行单次安全扫描
4. 每个目录扫描完成后：
   - 单独结果落盘至 `output/mirrored/<相对路径>/<目录名>.md`
   - 追加结果至 `output/combined_results.md`
5. 所有目录扫描完毕后退出；中途任何 AI 调用失败则立即终止

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

```bash
python main.py \
  --code-root D:\CodeScanner\TestCases \
  --ai-tool claudecode \
  --prompt-template D:\CodeScanner\TestCases\TestPrompt.md
```

`TestCases/` 下预埋了包含安全漏洞的示例代码：
- `module_a/db.py` — SQL 注入、明文密码、资源泄漏
- `module_a/config.py` — 硬编码凭据、命令注入
- `module_b/web.js` — 反射型 XSS
- `module_b/file_handler.py` — 路径遍历

## 注意事项

- 需要预先安装所选 AI 工具的 CLI 并确保在 PATH 中可用
- AI 调用为阻塞串行模式，大工程耗时较长，建议后台运行
- 日志双通道：控制台输出扫描进度，`scanner.log` 记录完整调试信息（CLI 命令、退出码、耗时）
- 遇到 AI 调用失败（非零退出码、超时、CLI 未找到）程序立即终止
