# C/C++ Case Statement Extractor & AI Scanner

## extract_cases.py — Case 标签提取

### 用途

扫描 C/C++ 源代码文件，提取指定行范围内所有 `case` 语句的行号及标签名（`case` 关键字与冒号之间的值），输出到 CSV 或 xlsx 文件中。

### 输入

通过命令行参数传入：

```
python extract_cases.py <文件路径> <起始行号> <结束行号> [csv|xlsx]
```

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| 文件路径 | 是 | — | C/C++ 源文件的绝对或相对路径 |
| 起始行号 | 是 | — | 要扫描的代码段起始行（1-based） |
| 结束行号 | 是 | — | 要扫描的代码段结束行（1-based） |
| csv\|xlsx | 否 | `csv` | 输出格式：`csv`（无需额外依赖）或 `xlsx`（需 `openpyxl`） |

### 输出

在当前目录生成 `case_statements.csv` 或 `case_statements.xlsx`，包含四列：

| 列名 | 说明 |
|------|------|
| 绝对路径 | 被扫描源文件的绝对路径 |
| 起始行号 | `case` 关键字所在的行号（1-based） |
| 结束行号 | 该 case 分支到下一个 `case`/`default`/`}` 之前的最后一行 |
| case标签 | `case` 关键字后、冒号前的值 |

- **CSV**：utf-8-sig 编码，WPS/Excel 直接双击打开不乱码
- **xlsx**：Excel 原生格式，需 `pip install openpyxl`

### 扫描规则

1. 仅扫描指定的行范围内（含起始行和结束行）的代码。
2. 匹配以 `case` 关键字开头的行（`case` 前可有任意空白字符）。
3. 提取 `case` 后、`:` 前的标签文本，去除首尾空白。
4. 自动过滤控制字符（`\x00`-`\x1f`、`\x7f`-`\x9f`），防止输出文件损坏。
5. 对以 `=`、`+`、`-`、`@` 开头的标签自动添加 `'` 前缀，防止 WPS/Excel 当作公式执行。
6. 不处理 `default:`，仅提取 `case` 分支。
7. 嵌套 switch 中的 case 同样会被提取。

### 编码兼容

自动尝试 UTF-8 解码；失败时回退到 GBK，兼容含中文注释的旧版 C/C++ 源文件。

---

## scan_cases.py — AI 逐 Case 扫描

### 用途

读取 `extract_cases.py` 生成的 CSV 或 xlsx 文件，逐行调用 ClaudeCode CLI 对每个 case 标签进行 AI 分析，结果写入新文件。

### 输入

```
python scan_cases.py --input <输入文件> --prompt-template <模板文件> [--output <输出文件>]
```

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | 是 | — | `extract_cases.py` 生成的 CSV 或 xlsx 文件路径 |
| `--prompt-template` | 是 | — | Prompt 模板文件路径（Markdown），含占位符 |
| `--output` | 否 | 与输入同格式，文件名为 `scan_results` | 输出文件路径（.csv 或 .xlsx） |
| `--auth-hints` | 否 | `无` | 用户指定的鉴权函数名列表（多个用逗号分隔，辅助 AI 识别） |

### Prompt 模板

模板文件中使用以下占位符，脚本执行时自动替换：

| 占位符 | 替换为 |
|--------|--------|
| `{file_path}` | 源文件绝对路径 |
| `{start_line}` | case 起始行号 |
| `{end_line}` | case 结束行号 |
| `{case_label}` | case 标签名（`case` 关键字后、冒号前的值） |
| `{auth_hints}` | 用户指定的鉴权函数提示列表 |

替换方式为 Python `str.replace()`，避免 C 代码中的 `{}` 字符干扰 `.format()`。

### 输出

生成与输入同格式的输出文件，包含四列：

| 列名 | 说明 |
|------|------|
| 绝对路径 | 源文件绝对路径 |
| 起始行号 | case 语句所在起始行号 |
| case标签 | case 标签名 |
| AI返回 | ClaudeCode CLI 的标准输出（AI 分析结果） |

### 调用方式

- 使用同目录下 `ai_client.py` 中的 `ClaudeCodeClient`（默认参数：max_turns=100, timeout=1000s）
- 工作目录（workdir）= 源文件所在目录（`os.path.dirname(绝对路径)`）；若目录不存在则回退到当前目录
- 直接通过 `subprocess.Popen` 传递 prompt 参数，不经过 shell，避免特殊字符/引号截断

### 错误处理

- 单行 AI 调用失败时：记录错误日志，将该行 AI 返回列标记为 `[AI调用失败] <错误信息>`，继续处理下一行
- 脚本会执行到所有行处理完毕，不会因单次失败而中断
- 日志同时输出到控制台和 `scan.log` 文件

### 依赖

- Python 3.7+
- openpyxl（仅读写 .xlsx 时需要：`pip install openpyxl`）
- 可正常运行的 ClaudeCode CLI（`claude` 命令在 PATH 中）

### 使用示例

```
# 第一步：提取 case 标签
python extract_cases.py ./src/worker.c 120 200          # 输出 CSV（默认）
python extract_cases.py ./src/worker.c 120 200 xlsx     # 输出 xlsx

# 第二步：AI 扫描每个 case
python scan_cases.py --input case_statements.csv --prompt-template audit_prompt.md

# 结果保存在 scan_results.csv 中
```

---

## 注意事项

- 行号以源文件第一行为 1。
- 不支持预处理宏内的 `case`（如 `#define CASE(n) case n:` 展开）。
- CSV 为默认格式，推荐给不需要 openpyxl 依赖的场景；若要 xlsx，手动传第三个参数 `xlsx`。
