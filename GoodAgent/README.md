# GoodAgent — 代码安全红线扫描系统

GoodAgent 是一个基于 opencode 的 **agent 编排式代码安全扫描系统**。
外部调用方通过 CLI 传入 JSON 参数，系统自动派发专用 subagent 执行安全规则检测，
经过 JSON 格式校验后返回结构化告警结果。

## 架构

```
                    外部调用方 (Python / 任意 CLI)
                            │
                    stdin JSON 参数
                            │
                            ▼
              ┌─────────────────────────┐
              │   sentinel (主 agent)     │
              │   • 参数验证              │
              │   • session 目录创建      │
              │   • checklist 自管理      │
              │   • subagent 派发         │
              │   • 结果聚合 → JSON      │
              └──────┬────────┬──────────┘
                     │        │
            ┌────────┘        └────────┐
            ▼                          ▼
┌──────────────────────┐   ┌──────────────────────┐
│ hardcoded-secret-    │   │ json-validator        │
│ scanner (subagent)   │   │ (subagent)            │
│                      │   │                      │
│ • 五维安全扫描       │   │ • Python json.loads() │
│ • 数据来源追溯       │   │ • 自动修复            │
│ • 误报排除           │   │ • 最多 3 次重试       │
│ • checklist 自管理   │   │ • checklist 自管理    │
└──────────────────────┘   └──────────────────────┘
                     │        │
                     ▼        ▼
              ┌─────────────────────────┐
              │   validation.ts          │
              │   (afterhook 插件)       │
              │   • checklist 完成检查   │
              │   • JSON 格式验证        │
              │   • 结果完整性检查       │
              │   • errors.log 记录      │
              └─────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │   emit_result.py         │
              │   • 解析 alerts.json     │
              │   • 生成 stdout JSON     │
              └─────────────────────────┘
                            │
                            ▼
                  stdout 一行合法 JSON
              (外部调用方读取解析)
```

## 执行流程

```
1. 外部 CLI: echo '<json>' | opencode run --agent sentinel
2. sentinel 解析 JSON → 验证参数 → 创建 session 目录 → 生成 checklist_sentinel.md
3. sentinel 派发 hardcoded-secret-scanner subagent
4. scanner 读取文件 → 五维扫描 → 追�?→ 误报排�?→ 返回告警表格
5. sentinel 解析表格 → JSON 转�?→ 写入 alerts.json
6. sentinel 派发 json-validator → Python json.loads() 校验 → 自动修复
7. validation.ts afterhook 检查所有 agent checklist 完成�?
8. emit_result.py 读取 alerts.json → 输出一行 stdout JSON
```

## 目录结构

```
GoodAgent/
├── .opencode/
│   ├── agents/
│   │   ├── sentinel.md                    # 主 agent (primary)
│   │   ├── hardcoded-secret-scanner.md    # 安全扫描 subagent
│   │   └── json-validator.md              # JSON 校验修复 subagent
│   ├── plugins/
│   │   └── validation.ts                  # afterhook 校验插件
│   ├── schemas/
│   │   ├── input.schema.json
│   │   ├── output-envelope.schema.json
│   │   └── alert.schema.json
│   ├── package.json
│   └── .gitignore
├── scripts/
│   ├── emit_result.py                     # stdout JSON 生成
│   └── validate_json.py                   # JSON 快速校验
├── tests/
│   └── fixtures/
│       ├── sample_with_secrets.py         # 含硬编码密码的测试文件
│       ├── sample_clean.py                # 无风险代码测试文件
│       ├── expected_output.json           # 预期结果
│       └── broken_alerts.json             # 格式错误 JSON（validator 测试用）
└── .gitignore
```

## 安装

### 前提

- **opencode** ≥ 1.18.4: `npm install -g opencode-ai`
- **Python** ≥ 3.6（emit_result.py / validate_json.py 使用）
- Node.js 依赖会在 opencode 启动时自动安装

### 打包

将本目录（GoodAgent/）完整复制到目标机器，或直接在工作目录中使用：

```bash
git clone <repo> GoodAgent
cd GoodAgent
```

无需额外构建步骤。`.opencode/` 目录下的 agent/plugin/schema 文件在 opencode 启动时自动加载。

## 使用

### 输入

stdin 传入一行 JSON，三个必填字段：

```json
{
  "code_path":     "/absolute/path/to/file.py",
  "code_snippet":  "DB_PASSWORD = \"Admin@123\"\nAPI_KEY = \"abc123\"",
  "session_id":    "scan-001"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code_path` | string | 代码文件的绝对路径。scanner 子 agent 优先通过此路径读取完整文件 |
| `code_snippet` | string | 代码片段文本。若 code_path 不可读，降级使用此内容。JSON 转义需要调用方预先处理 |
| `session_id` | string | 唯一会话标识，仅允许 `[a-zA-Z0-9._-]+`。用于输出目录隔离 |

### 调用

```bash
echo '{"code_path":"/path/to/code.py","code_snippet":"...","session_id":"s1"}' \
  | opencode run --agent sentinel
```

### 输出

#### stdout（一行 JSON，可直接 `json.loads()` 解析）

```json
{"session_id":"s1","status":"completed","output_file":"/abs/path/output/s1/alerts.json","alert_count":4,"summary":{"total_scanned":1,"high_risk":3,"medium_risk":1,"low_risk":0,"false_positive_likely":0}}
```

| 字段 | 说明 |
|------|------|
| `status` | `completed` / `partial` / `error` |
| `output_file` | 最终结果文件的绝对路径 |
| `alert_count` | 告警总数 |
| `summary.*` | 按严重度分类的告警统计 |

#### 磁盘文件

`output/{session_id}/` 目录包含：

| 文件 | 说明 |
|------|------|
| `alerts.json` | 完整告警结果，每个 Alert 对象含 `rule_id`, `severity`, `file`, `line`, `description`, `evidence` |
| `tmp/session.log` | 执行日志（关键事件时间线） |
| `tmp/checklist_sentinel.md` | sentinel 主 agent 执行 checklist |
| `tmp/checklist_hardcoded-secret.md` | scanner subagent 执行 checklist |
| `tmp/checklist_json-validator.md` | validator subagent 执行 checklist |
| `tmp/hardcoded-secret.json` | scanner 原始输出 |
| `tmp/errors.log` | afterhook 校验日志 |

### Alert 对象格式

```json
{
  "rule_id": "hardcoded-secret",
  "severity": "high",
  "file": "/path/to/file.py",
  "line": 2,
  "description": "明文密码硬编码",
  "evidence": "DB_PASSWORD = \"Admin@123\""
}
```

| severity | 含义 |
|----------|------|
| `high` | 源码明文密码、配置明文密钥、URL 嵌入密码 |
| `medium` | 配置疑似密钥、长 Base64 字符串 |
| `low` | Mock/调试密码、默认用户名 |
| `info` | 疑似误报（UUID、Git hash、颜色值等） |

## 安全扫描规则

hardcoded-secret-scanner 执行五维检测：

1. **密码/认证关键词** — `password`, `secret`, `token`, `api_key`, `jwt` 等
2. **硬编码密码特征** — `Admin@123` 等弱密码，32/64 位 hex 字符串
3. **Base64 编码密钥** — 长度 ≥32 的 Base64 字符串
4. **协议 URL 嵌入密码** — `http://user:pass@host` 格式
5. **配置文件特殊审计** — `.env`, `.yaml`, `.json` 配置文件逐行检查

每条告警经过数据来源追溯（字面量赋值/环境变量/安全存储/动态生成）和误报排除
（UUID v4、Git hash、CSS 颜色、公钥、注释引用等）后才确认。

## 示例：完整调用

```powershell
# 准备输入
$codePath = "D:\project\src\config.py"
$snippet = Get-Content $codePath -Raw
$input = @{
    code_snippet = $snippet
    code_path = $codePath
    session_id = "scan-" + (Get-Date -Format "yyyyMMdd-HHmmss")
} | ConvertTo-Json -Compress

# 执行扫描
$result = $input | opencode run --agent sentinel

# 解析结果
$envelope = $result | ConvertFrom-Json
Write-Output "Status: $($envelope.status)"
Write-Output "Alerts: $($envelope.alert_count)"

# 读取完整告警
$alerts = Get-Content $envelope.output_file | ConvertFrom-Json
$alerts.alerts | Format-Table severity, line, description
```

## 开发

### 新增安全规则

1. 在 `.opencode/agents/` 下创建新的 subagent profile（`.md` 文件）
2. 在 sentinel.md 的 `permission.task` 中添加新 agent 名称
3. 更新 sentinel 的编排步骤以派发新 subagent
4. 无需修改 afterhook 或其他组件

### 测试

```bash
# 运行自带测试 fixture
echo '{"code_path":"tests/fixtures/sample_with_secrets.py","code_snippet":"...","session_id":"test-1"}' \
  | opencode run --agent sentinel

# 检查 session.log
cat output/test-1/tmp/session.log

# 检查 checklist
cat output/test-1/tmp/checklist_sentinel.md
```
