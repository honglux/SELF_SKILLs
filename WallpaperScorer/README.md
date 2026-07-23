# WallpaperScorer

基于本地 LLM 的壁纸美学评分工具。将图片按**技术**和**美学**两条轨道拆分多个维度独立评分，支持**额外评分轮次**（Extra Pass）追加自定义维度。

## 项目结构

```
WallpaperScorer/
├── AI_scorer.py                         # 主模块：WallpaperScorer 类 + CLI 入口
├── batch_scorer.py                      # 批量评分：遍历文件夹 → CSV（支持 extra pass）
├── cluster_by_score.py                  # 聚类工具：读 CSV → 按分数拷贝图片
├── scoring_prompt.md                    # 原始合并版技术提示词（参考）
├── aesthetic_prompt.md                  # 原始合并版美学提示词（参考）
├── prompts/                             # 技术评分维度
│   ├── 01_structural_integrity.md       #   结构完整性与形变缺陷（max -5.0）
│   ├── 02_subject_integration.md        #   主体与背景整合 & 光照（max -3.0）
│   ├── 03_composition.md                #   构图与壁纸适配性（max -2.5）
│   ├── _fallback_recover.md             #   恢复提示词
│   └── _wallpaper_fitness.md            #   双满分回退提示词
├── prompts_aesthetic/                   # 美学评分维度
│   ├── 01_dynamic_lighting.md           #   动态光照与明暗对比（max -4.0）
│   ├── 02_cinematic_framing.md          #   电影式取景与空间深度（max -4.0）
│   ├── 03_color_harmony.md              #   色彩和谐与氛围深度（max -3.0）
│   ├── 04_rendering_quality.md          #   渲染质量（max -2.0）
│   └── _fallback_recover.md             #   恢复提示词
├── prompts_extra_default/               # 额外评分维度（默认目录，可自定义）
├── Test/                                # 测试图片
└── logs/                                # 运行日志（自动生成，已 gitignore）
```

## 整体逻辑

```
输入图片
    │
    ├─ Technical Suite (prompts/)
    │   ├─→ 结构完整性        → deduction
    │   ├─→ 主体与背景整合     → deduction
    │   └─→ 构图与适配性       → deduction
    │               │
    │               ▼ → Technical Score (1-10)
    │
    ├─ Aesthetic Suite (prompts_aesthetic/)
    │   ├─→ 动态光照          → deduction
    │   ├─→ 电影式取景        → deduction
    │   ├─→ 色彩和谐          → deduction
    │   └─→ 渲染质量          → deduction
    │               │
    │               ▼ → Aesthetic Score (1-10)
    │
    ├─ Extra Pass 1 (--extra 1, prompts_extra_default/)
    │   └─→ ...多个维度...    → Extra_1 Score (1-10)
    │
    ├─ Extra Pass 2 (--extra 2, 需 extra_1 已完成)
    │   └─→ ...               → Extra_2 Score (1-10)
    │
    └─ 双满分回退（tech=10 且 aesth=10 时触发）
```

- 每个维度独立调用视觉模型，降低单次上下文压力
- max_tokens=-1（无限制），深度思考模式
- 扣分支持 **0.5 增量** + **severity 等级系统**（subtle→minor→mild→moderate→severe）
- 任一维度失败时，自动触发**纯文本恢复**（thinking 回传）
- 双满分时触发**壁纸适配性终审**

### Extra Pass 机制

Extra pass 在 base pass 完成后按序执行，每轮有严格的依赖链：

| 命令 | 前置条件 | 写入列 |
|------|------|------|
| `--extra 1` | `technical_score` 已填 | `extra_1_score`, `extra_1_reason` |
| `--extra 2` | `extra_1_score` 已填 | `extra_2_score`, `extra_2_reason` |
| `--extra N` | `extra_{N-1}_score` 已填 | `extra_N_score`, `extra_N_reason` |

**总分公式**：`total_score = tech_score × 2 + aesthetic_score + extra_1 + extra_2 + ...`

Extra pass 也支持断点续接——已完成行自动跳过。

## 评分体系

### 技术评分（Technical Score）

| # | 维度 | 最大扣分 | 检查项 |
|---|------|:---:|------|
| 1 | 结构完整性与形变缺陷 | -5.0 | AI 痕迹（多余手指、肢体扭曲、物体融合）；线稿断裂/边界渗透 |
| 2 | 主体与背景整合 & 光照 | -3.0 | "贴纸感"（缺少阴影/接触点）；光源方向不一致 |
| 3 | 构图与壁纸适配性 | -2.5 | 主体被边缘尴尬裁切；缺少前景/中景/背景层次 |

### 美学评分（Aesthetic Score）

| # | 维度 | 最大扣分 | 检查项 |
|---|------|:---:|------|
| 1 | 动态光照与明暗对比 | -4.0 | 光照扁平无方向性；阴影发灰或高光溢出 |
| 2 | 电影式取景与空间深度 | -4.0 | 构图扁平缺乏景深；取景随意/背景杂乱；构图过度对称僵化 |
| 3 | 色彩和谐与氛围深度 | -3.0 | 调色板浑浊混乱；缺乏大气透视 |
| 4 | 渲染质量 | -2.0 | 颗粒噪点、过度锐化、视觉混沌杂乱 |

## 快速开始

### 环境

- Python 3.x + `openai` 库
- [LM Studio](https://lmstudio.ai/) 运行视觉模型（默认 `localhost:1234`）

### 批量评分

```bash
# Base pass（技术 + 美学）
python batch_scorer.py -i Test/ -o batch_output

# Extra pass（需 base pass 已完成）
python batch_scorer.py -i Test/ -o batch_output --extra 1
python batch_scorer.py -i Test/ -o batch_output --extra 2 --extra-prompts-dir my_prompts

# 按总分聚类拷贝
python cluster_by_score.py -c batch_output/scores.csv -o batch_output
```

| 参数 | 必填 | 默认值 | 说明 |
|------|:---:|------|------|
| `-i` `--input` | base pass 必填 | — | 图片文件夹（递归扫描） |
| `-o` `--output` | 否 | `batch_output` | 输出目录 |
| `--extra N` | 否 | 0 | 执行第 N 轮 extra pass |
| `--extra-prompts-dir` | 否 | `prompts_extra_default` | extra pass 的 prompt 目录 |
| `--debug` / `--no-debug` | 否 | on | 日志详细度 |

**CSV 字段**：`file_path`, `technical_score`, `aesthetic_score`, `extra_N_score`, `total_score`, `tech_reason`, `aesth_reason`, `extra_N_reason`……reason 格式：`[维度名 -扣分] 原因 | ...`

**断点续接**：再次运行相同命令时自动跳过已完成行。Extra pass 也支持——已填 `extra_N_score` 的行自动跳过。

**手动中断**：`Ctrl+C` 安全退出，已完成记录不丢失。

### 单图评分

```bash
python AI_scorer.py -i image.png
python AI_scorer.py -i image.png --no-debug
```

### 作为库调用

```python
from AI_scorer import WallpaperScorer, ScoreReport

# 默认 max_tokens=-1 深度思考
scorer = WallpaperScorer(prompts_dir="prompts", debug=False)
report = scorer.score("wallpaper.png")
print(report.final_score)
```

## 恢复机制

1. 收集该轮次的 **thinking 内容**
2. thinking + 部分输出 → 纯文本请求（不附带图片）
3. 提取结论 → 合法 JSON
4. 成功 → `recovered=True`；失败 → deduction=0

## API 配置

| 参数 | 默认值 | 说明 |
|------|------|------|
| `base_url` | `http://localhost:1234/v1` | LM Studio 默认地址 |
| `api_key` | `"lm-studio"` | 占位符 |
| `model` | `"local-model"` | LM Studio 通用模型标识 |
| `temperature` | `0.0` | 确定性输出 |
| `max_tokens` | **-1**（无限制） | 深度思考 |
| `timeout` | 1800s | HTTP 超时 |
| `max_retries` | 0 | 超时不重试 |

## 设计要点

- **维度拆分**：每个维度独立 prompt + 独立 API 调用，降低上下文压力
- **Extra pass 链**：依赖链保证执行顺序，支持断点续接
- **Severity 等级系统**：subtle→minor→mild→moderate→severe，精细量化扣分
- **双满分回退**：完美分自动触发壁纸适配性终审
- **thinking 感知**：自动检测并记录模型内部推理
- **容错恢复**：截断/异常自动回退
- **可扩展**：增删维度只需操作 `.md` 文件
- **零网络依赖**：所有处理在本地完成
