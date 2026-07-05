# WallpaperScorer

基于本地 LLM 的壁纸美学评分工具。将图片按**技术**和**美学**两条轨道拆分多个维度独立评分，最终输出两个 1-10 分的独立分数。

支持**标准模式**和**全力模式**（`--full`）：标准模式限制思考深度以求速度，全力模式放开所有限制追求最高准确度。

## 项目结构

```
WallpaperScorer/
├── AI_scorer.py                         # 主模块：WallpaperScorer 类 + CLI 入口
├── batch_scorer.py                      # 批量评分：遍历文件夹 → CSV + 聚类
├── scoring_prompt.md                    # 原始合并版技术提示词（参考）
├── aesthetic_prompt.md                  # 原始合并版美学提示词（参考）
├── prompts/                             # 标准模式 — 技术评分维度
│   ├── 01_structural_integrity.md       #   结构完整性与形变缺陷（max -4.0）
│   ├── 02_subject_integration.md        #   主体与背景整合 & 光照（max -3.0）
│   ├── 03_composition.md                #   构图与壁纸适配性（max -2.5）
│   ├── _fallback_recover.md             #   恢复提示词（截断/报错时自动使用）
│   └── _wallpaper_fitness.md            #   双满分回退提示词
├── prompts_full/                        # 全力模式 — 技术评分维度（无思考约束）
│   └── ...（同 prompts/，思考约束改为深度模式）
├── prompts_aesthetic/                   # 标准模式 — 美学评分维度
│   ├── 01_dynamic_lighting.md           #   动态光照与明暗对比（max -4.0）
│   ├── 02_cinematic_framing.md          #   电影式取景与空间深度（max -3.0）
│   ├── 03_color_harmony.md              #   色彩和谐与氛围深度（max -3.0）
│   └── _fallback_recover.md             #   恢复提示词
├── prompts_aesthetic_full/              # 全力模式 — 美学评分维度（无思考约束）
│   └── ...（同 prompts_aesthetic/，思考约束改为深度模式）
├── Test/                                # 测试图片
└── logs/                                # 运行日志（自动生成，已 gitignore）
```

## 整体逻辑

```
输入图片
    │
    ├─ Technical Suite (prompts/ 或 prompts_full/)
    │   ├─→ 结构完整性        → deduction
    │   ├─→ 主体与背景整合     → deduction
    │   └─→ 构图与适配性       → deduction
    │               │
    │               ▼ → Technical Score (1-10)
    │
    ├─ Aesthetic Suite (prompts_aesthetic/ 或 prompts_aesthetic_full/)
    │   ├─→ 动态光照          → deduction
    │   ├─→ 电影式取景        → deduction
    │   └─→ 色彩和谐          → deduction
    │               │
    │               ▼ → Aesthetic Score (1-10)
    │
    └─ 双满分回退（tech=10 且 aesth=10 时触发）
        └─→ 壁纸适配性终审 → 替换美学分
```

- 每条轨道独立运行，各自拥有一组维度 prompt 文件
- 每个维度独立调用视觉模型，降低单次上下文压力
- 扣分支持 **0.5 增量**（0.5, 1.0, 1.5, 2.0…），不再全有或全无
- 任一维度失败时，自动触发**纯文本恢复**（thinking 回传，不重发图片）
- 技术与美学双满分时，触发**壁纸适配性终审**（`_wallpaper_fitness.md`）

## 评分体系

### 技术评分（Technical Score）

| # | 维度 | 最大扣分 | 检查项 |
|---|------|:---:|------|
| 1 | 结构完整性与形变缺陷 | -4.0 | AI 痕迹（多余手指、肢体扭曲、物体融合）；线稿断裂/边界渗透 |
| 2 | 主体与背景整合 & 光照 | -3.0 | "贴纸感"（缺少阴影/接触点）；光源方向不一致 |
| 3 | 构图与壁纸适配性 | -2.5 | 主体被边缘尴尬裁切；缺少前景/中景/背景层次 |

### 美学评分（Aesthetic Score）

| # | 维度 | 最大扣分 | 检查项 |
|---|------|:---:|------|
| 1 | 动态光照与明暗对比 | -4.0 | 光照扁平无方向性；阴影发灰或高光溢出，缺乏电影级动态范围 |
| 2 | 电影式取景与空间深度 | -3.0 | 构图扁平缺乏景深；取景随意（头部空间不当、背景杂乱抢镜） |
| 3 | 色彩和谐与氛围深度 | -3.0 | 调色板浑浊混乱无统一情绪；缺乏大气透视（雾霭、光线衰减） |

> 扣分规则：**0.5 增量**，鼓励部分扣分而非全有或全无。Prompt 内要求严格审视，不轻易给满分。

## 快速开始

### 环境

- Python 3.x + `openai` 库
- [LM Studio](https://lmstudio.ai/)（或其他 OpenAI 兼容 API）运行视觉模型
- 启动 LM Studio 本地 server（默认 `localhost:1234`）

### 单图评分

```bash
# 标准模式（默认）
python AI_scorer.py -i image.png

# 全力模式（-1 token、深度思考、无字数约束）
python AI_scorer.py -i image.png -f

# 关闭 debug 输出
python AI_scorer.py -i image.png --no-debug
```

| 参数 | 必填 | 默认值 | 说明 |
|------|:---:|------|------|
| `-i` `--image` | 是 | — | 待评分图片路径 |
| `-f` `--full` | 否 | off | 全力模式：max_tokens=-1，使用深度思考 prompt |
| `-d` `--prompts-dir` | 否 | `prompts` | 技术评分 prompt 目录（非 full 模式） |
| `--prompts-aesthetic-dir` | 否 | `prompts_aesthetic` | 美学评分 prompt 目录（非 full 模式） |
| `--debug` | 否 | on | 日志输出完整 thinking 与 raw output |
| `--no-debug` | 否 | — | 精简日志 |

### 批量评分

```bash
# 标准模式批量
python batch_scorer.py -i Test/ -o batch_output

# 全力模式批量
python batch_scorer.py -i Test/ -o batch_output -f
```

| 参数 | 必填 | 默认值 | 说明 |
|------|:---:|------|------|
| `-i` `--input` | 是 | — | 图片文件夹（递归扫描） |
| `-o` `--output` | 否 | `batch_output` | 输出目录 |
| `-f` `--full` | 否 | off | 全力模式 |
| `--debug` / `--no-debug` | 否 | on | 日志详细度 |

**输出：**
- `batch_output/scores.csv` — 逐行即时写入（完成一张写一行），支持断点续接。字段：`file_path`（绝对路径）, `technical_score`, `aesthetic_score`, `total_score`, `tech_reason`, `aesth_reason`
- `batch_output/<total_score>/` — 按总分聚类文件夹，复制图片

**断点续接**：再次运行相同命令时，自动读取已有 CSV 中 `file_path` 列，跳过已完成的图片，只处理剩余。CSV 以追加模式写入，不会覆盖已有记录。

**手动中断**：`Ctrl+C` 安全退出——已完成图片的 CSV 记录和聚类文件不丢失，下次运行自动续接。

> **总分公式**：`total_score = tech_score × 2 + aesthetic_score`（范围 3~30）

### 作为库调用

```python
from AI_scorer import WallpaperScorer, ScoreReport, DimensionResult

# 标准模式
scorer = WallpaperScorer(prompts_dir="prompts", debug=False)
report = scorer.score("wallpaper.png")

# 全力模式
scorer_full = WallpaperScorer(prompts_dir="prompts_full", max_tokens=-1, debug=False)
report_full = scorer_full.score("wallpaper.png")

# 访问结果
print(report.final_score)
for d in report.dimensions:
    print(d.name, d.deduction, d.reason, d.recovered)
```

## 模式对比

| | 标准模式 | 全力模式 (`-f`) |
|------|:---:|:---:|
| prompt 目录 | `prompts/` + `prompts_aesthetic/` | `prompts_full/` + `prompts_aesthetic_full/` |
| max_tokens | 4096 | **-1**（无限制） |
| 思考约束 | 10 段落/项，不反复推敲 | **无限制**，鼓励多角度深度审视 |
| 速度 | 快 (~5min/图) | 慢 (可能 15-30min/图) |
| 准确度 | 中等 | 高 |

## 恢复机制

当模型输出被截断或 JSON 无效时：

1. 收集该轮次的 **thinking 内容**
2. 将 thinking + 部分输出拼接，发纯文本请求（不附带图片）
3. 提取结论，输出合法 JSON
4. 成功 → `recovered=True`；失败 → deduction=0

## API 配置

| 参数 | 默认值 | 说明 |
|------|------|------|
| `base_url` | `http://localhost:1234/v1` | LM Studio 默认地址 |
| `api_key` | `"lm-studio"` | 占位符，本地服务不需要真实密钥 |
| `model` | `"local-model"` | LM Studio 通用模型标识 |
| `temperature` | `0.0` | 确定性输出 |
| `max_tokens` | 4096（标准）/ -1（全力） | 单轮 token 上限 |
| `timeout` | 1800s | HTTP 超时 |
| `max_retries` | 0 | 超时不重试 |

## 设计要点

- **双轨独立评分**：技术与美学各自独立，互不干扰
- **双模式**：标准模式快速筛选，全力模式深度评估
- **维度拆分**：每个维度独立 prompt + 独立 API 调用，降低上下文压力
- **0.5 增量扣分**：鼓励精细评分，避免全有或全无
- **双满分回退**：完美分自动触发壁纸适配性终审
- **thinking 感知**：自动检测并记录模型内部推理
- **容错恢复**：截断/异常自动回退，不丢数据
- **可扩展**：增删维度只需操作 `.md` 文件
- **零网络依赖**：所有处理在本地完成
