---
name: crypto-extractor
description: |
  [V2改进版] 从工程源码中提取所有加密算法、加密函数和加密相关配置。在V1基础上增强：标准表格输出替代JSON、仅记录有发现文件、强化提问流程、主Agent过滤修复建议。当用户提到"提取加密"、"加密算法检视"、"加密白盒测试"、"加密函数提取"、"加密代码审计"时触发此skill。
---

# 加密算法提取测试执行 Skill (V2)

本 skill 用于从工程源码中系统性地提取所有加密算法、加密函数和加密相关配置，生成完整的加密使用清单。

---

## 一、工作流程

### 1.1 核心流程（必须遵循）

```
用户请求 → 向用户询问确认 → 撰写测试计划 → 再次用户确认 → 执行测试 → 生成最终报告
```

**流程说明**：
1. **询问确认阶段**：收集测试范围、输出路径、排除项等关键信息
2. **测试计划撰写**：生成详细的测试计划文档
3. **用户确认计划**：用户审核并确认测试计划
4. **执行测试阶段**：按计划逐文件执行加密提取
5. **生成最终报告**：汇总统计和分类报告

### 1.2 执行原则（必须遵循）

| 原则 | 说明 |
|------|------|
| **分步执行** | 按文件或小模块逐一测试，不批量执行 |
| **即时落盘** | 每完成一个文件/模块测试后，立即将结果写入文件 |
| **过滤修复建议** | SubAgent 结果写入前，主 Agent 检查并删除修复性内容 |
| **结果追加** | 后续测试结果追加到已有结果文件中 |
| **仅记录有发现** | 只写入有加密使用的文件，无加密文件不写入结果 |
| **Subagent机制** | 每个文件启动独立上下文的 subagent，完成后释放 |
| **标注位置** | 发现加密使用时标注具体文件路径和代码行号 |
| **仅记录发现** | 记录加密使用事实，不提供安全评估或修复建议 |

---

## 二、询问确认阶段

### 2.1 提问规范（必须执行，不可跳过）

**此阶段绝对不可跳过。** 在收集到所有必问信息之前，禁止开始测试。

**逐一提问**：每次只问 1~2 个问题，等用户回答后再问下一批。

**第 1 轮（必问）**：
> 1. 检视根目录路径？（如 `entry/src/main/ets`、`src/`）
> 2. 测试结果输出目录？（默认 `<根目录>/TestPlan/EncryptionTest/`）

等待用户回复后，继续第 2 轮。

**第 2 轮（必问）**：
> 3. 文件类型和排除范围？（默认扫描所有代码文件，排除 `node_modules/`、`dist/`、`.md`）
> 4. 是否有加密相关的重点目录需要优先处理？（如 `security/`、`crypto/`、`auth/`）

等待用户回复后，口头总结关键参数，确认无误后进入测试计划阶段。

---

## 三、测试计划撰写阶段

### 3.1 测试计划文档结构

用户确认参数后，生成测试计划文档 `EncryptionExtractionTestPlan.md`：

```markdown
# 加密函数提取测试指导文档

> 创建时间: YYYY-MM-DD
> 测试范围: [用户指定的检视根目录]
> 测试项目: 加密方式和算法提取（白盒代码检视）

---

## 一、测试概述

### 1.1 测试目的
从源码层面检视工程中所有代码文件，提取加密方式、算法及相关实现。

### 1.2 测试方法
采用逐文件扫描 + Subagent机制，避免上下文溢出。

### 1.3 预期产出
- 测试计划文档: {输出目录}/EncryptionExtractionTestPlan.md
- 测试结果文档: {输出目录}/EncryptionExtractionResults.md

---

## 二、测试范围界定

### 2.1 测试目录
[列出所有需要扫描的目录和文件数量统计]

### 2.2 排除范围
[列出排除的目录和文件类型]

---

## 三、加密识别关键词清单

[根据检测语言生成对应的关键词列表]

---

## 四、测试执行原则

[复制 1.2 执行原则表格]

---

## 五、测试步骤

### 5.1 Subagent Prompt 模板
[提供标准化的 subagent 调用模板]

---

## 六、输出文件格式规范

[定义结果文件的 Markdown 格式]
```

### 3.2 用户确认模板

测试计划生成后，询问用户确认：

```
【测试计划已生成】

测试计划文档已保存至: {输出目录}/EncryptionExtractionTestPlan.md

请确认：
- 测试范围是否正确？
- 加密关键词清单是否完整？
- 是否需要补充或修改？

确认无误后回复"开始测试"执行测试，或提出修改意见。
```

---

## 四、测试执行阶段

### 4.1 Subagent 工作流程

```
主 Agent
    │
    │ 1. 获取文件列表
    │
    │ 2. 对每个文件：
    │    ├── 启动 Subagent (独立上下文)
    │    │   ├── Subagent 接收文件路径
    │    │   ├── Subagent 使用 Read 工具读取文件
    │    │   ├── Subagent 根据关键词识别加密使用
    │    │   ├── Subagent 返回表格格式结果
    │    │
    │    ├── 主 Agent 接收 Subagent 结果
    │    ├── 主 Agent 追加写入结果文件
    │    ├── Subagent 上下文释放
    │    │
    │ 3. 继续下一个文件
    │
    │ 4. 最终汇总
```

### 4.2 Subagent Prompt 模板

对每个文件使用以下模板调用 subagent：

```
【加密提取任务】

请阅读以下源文件并提取加密相关代码信息：

**文件路径**: {FILE_PATH}

**任务要求**:
1. 使用 Read 工具完整读取该文件
2. 搜索加密关键词：[根据语言从 Section 5 关键词清单中选取]

3. 对每个发现的加密使用，提取以下信息：
   - 加密类型分类：消息摘要|对称加密|非对称加密|HMAC|随机数生成|密钥派生|密钥存储|编码转换
   - 具体函数/API名称
   - 代码行号（精确到行）
   - 使用场景简述
   - 上下文标注：注明该加密是核心功能使用还是仅引用/导入/注释提及

4. 返回格式（表格）：
| 行号 | 加密类型 | 具体API | 使用场景 | 上下文 |
|------|---------|--------|---------|--------|
上下文标注: [核心使用] / [模块导入] / [注释提及] / [配置引用]

**重要约束 — 必须遵守**：
- 仅记录发现，绝对不提供修复方案或修复建议
- 不提供安全评估（如"使用了不安全算法"）
- 精确标注行号，不要遗漏 import 语句中的加密模块引用
- 若文件中无加密使用，输出: "无加密使用"

请返回完整的提取结果。
```

### 4.3 结果落盘策略

| 阶段 | 落盘时机 | 文件操作 |
|------|----------|----------|
| 单文件测试完成 | 每个 Subagent 返回后 | **追加写入**结果文件 |
| 目录测试完成 | 一个目录完成后 | 可选：追加目录小结 |
| 全量测试完成 | 所有文件完成后 | 在结果文件末尾追加汇总统计 |

### 4.4 结果追加方式

使用 Edit 工具追加内容到结果文件。**仅记录有加密发现的文件**：

```markdown
| {序号} | {相对文件路径} | {加密类型} | {具体API} | {行号} | {使用场景} | {上下文} |
```

无加密使用的文件仅更新进度日志（标记为已完成），不写入结果表格。避免结果文件被大量"无加密使用"行淹没。

---

## 五、加密关键词清单

### 5.1 多语言通用关键词

| 分类 | 关键词 |
|------|--------|
| **编码转换** | Base64, base64, encode, decode, btoa, atob, hex, binary |
| **密钥相关** | password, secret, key, token, nonce, iv, salt, authTag, credential |
| **安全相关** | encrypt, decrypt, hash, cipher, signature, authentication, crypto |
| **证书相关** | cert, certificate, x509, ssl, tls, pem, der |

### 5.2 ArkTS/TypeScript/JavaScript 关键词

| 分类 | 关键词 |
|------|--------|
| **模块导入** | cryptoFramework, huks, @kit.CryptoArchitectureKit, @kit.UniversalKeystoreKit |
| **消息摘要** | createMd, digest, update, SHA256, SHA384, SHA512, SHA1, MD5 |
| **对称加密** | createCipher, createSymKeyGenerator, AES256, AES128, GCM, CBC, CTR, convertKey |
| **非对称加密** | createAsyKeyGenerator, RSA2048, RSA1024, RSA512, RSA3072, PKCS1, OAEP |
| **HUKS** | generateKeyItem, initSession, finishSession, abortSession, HuksTag, HuksKeyAlg |
| **随机数** | createRandom, generateRandom, getRandomValues |
| **Web Crypto** | crypto.subtle, SubtleCrypto, digest, encrypt, decrypt, sign, verify, generateKey, deriveKey |
| **密钥派生** | PBKDF2, HKDF, ECDH, importKey, exportKey, wrapKey, unwrapKey |

### 5.3 Java 关键词

| 分类 | 关键词 |
|------|--------|
| **加密类** | Cipher, MessageDigest, Mac, Signature, KeyGenerator, KeyPairGenerator |
| **算法名** | AES, RSA, DES, SHA-256, MD5, HmacSHA256, PBKDF2 |
| **密钥类** | SecretKey, PublicKey, PrivateKey, KeySpec, KeyFactory |
| **证书类** | Certificate, X509Certificate, KeyStore, TrustManager |
| **随机数** | SecureRandom, SecureRandom.getInstanceStrong |
| **工具类** | Base64, Base64.getEncoder(), Base64.getDecoder() |

### 5.4 Python 关键词

| 分类 | 关键词 |
|------|--------|
| **标准库** | hashlib, hmac, secrets, cryptography, Crypto, PyCryptodome |
| **函数名** | hashlib.sha256, hashlib.md5, hmac.new, secrets.token_bytes |
| **算法名** | AES, RSA, DES, SHA256, MD5, HMAC |
| **加密类** | Cipher, AES.new, RSA.generate, PKCS1_OAEP |
| **密钥类** | generate_key, load_key, private_key, public_key |
| **编码** | base64.b64encode, base64.b64decode, binascii.hexlify |
| **随机数** | secrets.randbelow, secrets.token_hex, secrets.token_urlsafe |
| **证书类** | ssl, certifi, OpenSSL |

### 5.5 C/C++ 关键词

| 分类 | 关键词 |
|------|--------|
| **OpenSSL** | EVP_CIPHER_CTX, EVP_aes_256_gcm, EVP_sha256, RSA, HMAC |
| **函数名** | EVP_EncryptInit, EVP_EncryptUpdate, EVP_DecryptFinal, RSA_public_encrypt |
| **算法名** | AES, RSA, SHA256, MD5, HMAC |
| **头文件** | openssl/aes.h, openssl/rsa.h, openssl/sha.h, openssl/hmac.h |
| **随机数** | RAND_bytes, RAND_seed, random_bytes |
| **编码** | BIO_new, BIO_read, BIO_write, base64_encode |
| **证书类** | X509, SSL_CTX, SSL_connect, PEM_read_X509 |

### 5.6 Go 关键词

| 分类 | 关键词 |
|------|--------|
| **标准库** | crypto/aes, crypto/rsa, crypto/sha256, crypto/hmac, crypto/rand |
| **函数名** | aes.NewCipher, rsa.GenerateKey, sha256.Sum256, hmac.New |
| **随机数** | rand.Read, rand.Prime |
| **证书类** | crypto/x509, tls, tls.Config |
| **编码** | encoding/base64, base64.StdEncoding, hex.EncodeToString |

### 5.7 Rust 关键词

| 分类 | 关键词 |
|------|--------|
| ** crates** | aes, rsa, sha2, hmac, rand, ring, openssl |
| **函数名** | Aes256Gcm::new, Rsa::generate, Sha256::digest, Hmac::new |
| **算法名** | AES, RSA, SHA256, HMAC, ChaCha20 |
| **随机数** | rand::thread_rng, rand::Rng, rand::rngs::OsRng |
| **证书类** | rustls, webpki, x509-parser |

### 5.8 C# 关键词

| 分类 | 关键词 |
|------|--------|
| **命名空间** | System.Security.Cryptography, System.Security.Cryptography.X509Certificates |
| **类名** | Aes, Rsa, SHA256, MD5, HMACSHA256, RNGCryptoServiceProvider |
| **函数名** | CreateEncryptor, CreateDecryptor, ComputeHash, GenerateKey |
| **证书类** | X509Certificate2, X509Store, StoreLocation |
| **随机数** | RandomNumberGenerator, GetBytes |
| **编码** | Convert.ToBase64String, Convert.FromBase64String |

---

## 六、输出文件格式规范

### 6.1 结果文件头部

```markdown
# 加密函数提取测试结果

> 测试时间: YYYY-MM-DD
> 测试范围: [检视根目录]
> 总文件数: {数量}
> 发现加密使用文件数: {数量}

---

## 一、提取结果列表

| 序号 | 文件路径 | 加密类型 | 具体函数/API | 行号 | 使用场景 |
|------|----------|----------|--------------|------|----------|
```

### 6.2 结果文件汇总

测试完成后追加：

```markdown
---

## 二、按目录汇总

[每个目录的统计信息]

---

## 三、加密类型统计

| 加密类型 | 文件数 | 主要使用场景 |
|----------|--------|--------------|
[加密类型统计表]

---

## 四、核心加密实现文件

[关键加密文件清单]

---

## 五、测试完成时间

- 开始时间: YYYY-MM-DD HH:MM
- 结束时间: YYYY-MM-DD HH:MM
- 测试方法: 逐文件扫描 + Subagent独立上下文机制
- 结果落盘: 每目录完成后追加写入
```

---

## 七、进度追踪

### 7.1 TodoWrite 使用

使用 todowrite 工具追踪测试进度：

```json
[
  { "content": "向用户询问确认测试参数", "status": "completed/in_progress", "priority": "high" },
  { "content": "生成测试计划文档", "status": "pending", "priority": "high" },
  { "content": "等待用户确认测试计划", "status": "pending", "priority": "high" },
  { "content": "测试 [目录名] ({文件数}文件)", "status": "pending", "priority": "high" },
  ...
  { "content": "生成最终汇总报告", "status": "pending", "priority": "high" }
]
```

### 7.2 异常处理

| 异常情况 | 处理方式 |
|----------|----------|
| 文件读取失败 | 记录"读取失败"，继续下一个文件 |
| Subagent 超时 | 超时后记录"超时"，继续下一个文件 |
| Subagent 返回格式错误 | 尝试解析，失败则记录"格式错误"，继续下一个文件 |

---

## 八、注意事项

### 8.1 安全规范

- **敏感信息脱敏**: 密钥、密码、认证头等敏感信息在日志中必须使用 `%{private}s` 或类似脱敏格式
- **仅记录发现**: 不提供安全评估或修复建议，仅记录加密使用事实
- **不泄露密钥**: 严禁在结果文档中记录具体的密钥值或密码明文

### 8.2 语言适配

- 根据项目语言自动选择对应的关键词清单
- 多语言项目时合并使用各语言关键词
- 支持用户自定义关键词补充

### 8.3 Subagent 释放

- 每个 subagent 完成后立即释放上下文
- 不保留文件内容在主 agent 上下文中
- 仅保留表格格式的提取结果用于落盘

---

## 九、完整执行示例

### 9.1 询问阶段

```
【加密提取测试准备】

请确认以下测试参数：

1. 检视根目录: D:\my-project\src
2. 输出目录: D:\my-project\TestPlan\EncryptionTest
3. 文件类型: .ets, .ts, .js, .vue (默认)
4. 排除范围: node_modules/, .md 文件 (默认)
5. 优先目录: security/ (建议)

请回复确认或提出修改。
```

### 9.2 测试计划确认

```
【测试计划已生成】

测试计划文档: D:\my-project\TestPlan\EncryptionTest\EncryptionExtractionTestPlan.md

预计扫描 150 个文件，主要分布在以下目录：
- security/ (5文件) - 优先
- service/ (30文件)
- utils/ (20文件)
- ...

确认无误后回复"开始测试"执行。
```

### 9.3 执行阶段输出

```
【测试进度】
✓ security/ 目录完成 (5文件, 15条加密记录已落盘)
→ service/ 目录进行中 (已完成 10/30 文件)
...
```

### 9.4 最终报告

```
【测试完成】

测试结果文档: D:\my-project\TestPlan\EncryptionTest\EncryptionExtractionResults.md

统计:
- 总文件数: 150
- 加密使用文件: 35
- 加密记录数: 120

主要加密类型:
- AES-GCM: 25次 (密码存储)
- SHA-256: 15次 (消息摘要)
- RSA: 10次 (密码传输)
- ...
```

---

*本 skill 适用于通用语言的加密算法提取，遵循分步测试、即时落盘、Subagent释放原则。*