---
name: random-security-audit-v3
description: "[V3非交互版] 密码学安全随机数使用合规性审计。非交互单轮模式,仅扫描当前目录文件(不递归子目录),结果写入AI测试结果.md。检视安全敏感场景是否使用CSPRNG。当用户提到随机数审计/CSPRNG合规/random security audit时触发此skill。"
---

# 随机数安全审计 (V3)

**执行模式**：非交互单轮，直接执行，不提问不确认。**仅扫描当前工作目录下的文件，不访问子目录。** 结果写入当前目录的 `AI测试结果.md`。

---

## 一、安全敏感场景判定

### 明确安全场景 → 必须用 CSPRNG
- 生成密钥（AES/SM4/RSA/ECC）、IV、Nonce
- 认证协议（Digest Auth cnonce、OAuth state）
- 安全 Token（Session、CSRF、密码重置）
- 防重放字段
- Salt 用于密码哈希
- ECC 随机数 k

### 可能安全场景 → 建议用 CSPRNG
- 唯一标识符（若可被猜测）
- 随机端口/文件名（视上下文）
- 验证码/OTP

### 非安全场景 → 可用非 CSPRNG
- UI 动画/颜色
- 游戏机制（非安全关键）
- 数据洗牌/排序（非安全关键）

## 二、语言随机数函数对照

| 语言 | CSPRNG（安全） | 非CSPRNG（不安全） |
|------|---------------|-------------------|
| ArkTS/TS/JS | `cryptoFramework.createRandom()`, `crypto.subtle`, `crypto.getRandomValues()` | `Math.random()`, `Date.now()` 作为随机源 |
| Java | `SecureRandom`, `SecureRandom.getInstanceStrong()` | `java.util.Random`, `Math.random()` |
| Python | `secrets.token_*`, `os.urandom()`, `random.SystemRandom` | `random.random()`, `random.randint()` |
| Go | `crypto/rand.Read()`, `crypto/rand.Prime()` | `math/rand.Intn()` |
| C/C++ | `RAND_bytes()`, `RAND_priv_bytes()` | `rand()`, `srand()`, `random()` |
| Rust | `rand::rngs::OsRng`, `ring::rand` | `rand::thread_rng` 在非安全场景 |
| C# | `RandomNumberGenerator`, `RNGCryptoServiceProvider` | `System.Random` |
| Swift | `SecRandomCopyBytes` | `arc4random` (视场景) |

## 三、字段名 vs 函数调用

- `random: string`（接口/类型定义中的字段名） → 不算随机数生成
- `Math.random()`（实际函数调用） → 算随机数生成

---

## 四、Subagent 使用

对当前目录下每个源文件（排除 .md 和 AI测试结果.md），启动独立 subagent：

```
你是随机数安全审计 Agent。阅读文件，检查随机数生成合规性。

文件: {FILE_PATH}

搜索所有随机数生成函数调用，对每个命中分析上下文：
- 安全场景（加密/认证/Token/Salt/IV/Nonce/cnonce）→ 必须用CSPRNG，否则为缺陷
- 非安全场景（UI动画/颜色/排序）→ 可用非CSPRNG

CSPRNG函数（根据文件语言选取安全函数列表）
不安全函数（根据文件语言选取非CSPRNG列表）

字段名不等于函数调用：random: string 类型定义不算

仅记录发现，不提供修复方案。理由仅说明为什么合规/缺陷，不延伸到如何修改。

输出格式：
| 行号 | 函数/模式 | 代码片段 | 上下文场景 | 合规判断 | 理由 |
合规判断: ✅合规 / ❌缺陷 / ⚠️待确认
若无: "无随机数生成代码"
小结: 共发现 N 处，合规 M 处，缺陷 K 处。
```

---

## 五、输出格式

```markdown
# 随机数安全审计结果

> 扫描范围：仅当前目录

## 发现列表
| 序号 | 文件 | 行号 | 函数 | 代码片段 | 场景 | 判断 | 理由 |
|------|------|------|------|---------|------|------|------|

## 统计
| 项目 | 数量 |
|------|------|
| 总发现 | N |
| 合规 | N |
| 缺陷 | N |

## 缺陷清单
（逐一列出文件、行号、问题描述）

## 总结
共扫描 N 个文件，发现 M 处随机数使用，K 处缺陷。
```
