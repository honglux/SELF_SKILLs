---
name: cert-test-v3
description: "[V3非交互版] 证书使用场景白盒测试执行器。非交互单轮模式,仅扫描当前目录文件(不递归子目录),结果写入AI测试结果.md。检视证书加载/解析/验证/密钥使用/TLS配置/硬编码凭据等是否合规。当用户提到证书测试/证书审计/cert test/TLS安全测试时使用。"
---

# 证书使用场景白盒测试 (V3)

**执行模式**：非交互单轮，直接执行，不提问不确认。**仅扫描当前工作目录下的文件，不访问子目录。** 结果写入当前目录的 `AI测试结果.md`。

---

## 一、分析维度

| # | 维度 | 检查内容 |
|---|------|---------|
| 1 | 证书加载 | 证书文件读取（.pem, .p12, .pfx, .cer, .crt, .der, .p7b） |
| 2 | 证书解析 | 证书字段解析（Subject, Issuer, Serial, NotBefore, NotAfter, PublicKey, SAN） |
| 3 | 证书验证 | 签名验证、证书链校验、有效期检查、吊销检查；特别注意跳过验证的配置 |
| 4 | 证书/密钥存储 | HUKS, KeyStore, localStorage, fileSystem 等存储操作 |
| 5 | 密钥使用 | 公钥/私钥加解密、签名、验签操作 |
| 6 | TLS/HTTPS 配置 | TLS 版本、caPath、clientCert、key、rejectUnauthorized |
| 7 | 硬编码凭据 | 证书字符串、私钥、密钥材料、密码 |
| 8 | 算法强度 | 加密算法及密钥长度 |
| 9 | 有效期 | notBefore/notAfter 相关代码 |
| 10 | 权限声明 | 证书相关系统权限 |

## 二、跳过验证模式（重点关注）

| 语言 | 跳过模式 |
|------|---------|
| ArkTS | `remoteValidation: 'skip'` |
| Java | `verifyFalse`, `trustAllCerts` |
| Python | `verify=False`, `check_hostname=False` |
| Go | `InsecureSkipVerify: true` |
| JS/TS | `rejectUnauthorized: false` |
| Rust | `danger_accept_invalid_certs()` |
| C# | `ServerCertificateValidationCallback` 返回 true |

---

## 三、风险等级

| 等级 | 典型场景 |
|------|---------|
| 极高 | 凭据明文存储、硬编码私钥 |
| 高 | skip 证书验证、禁用 CA 检查、硬编码密码 |
| 中 | 证书白名单缺失、路径暴露 |
| 低 | 内存驻留密钥（需 root）、受限环境 |
| 信息 | 证书数据模型定义、算法使用记录 |

---

## 四、Subagent 使用

对当前目录下每个源文件（排除 .md 和 AI测试结果.md），启动独立 subagent：

```
你是证书安全审计 Agent。阅读文件，按10个维度分析证书使用安全性。

文件: {FILE_PATH}

分析维度：证书加载、证书解析、证书验证、密钥存储、密钥使用、TLS配置、硬编码凭据、算法强度、有效期、权限声明

重点关注：跳过验证的配置、硬编码证书/私钥/密码

仅记录发现，不提供修复方案。

输出格式：
| # | 维度 | 行号 | 风险 | 描述 |
每行格式: {事实} → {安全影响}
若无: "该文件未涉及证书使用相关代码"
```

---

## 五、输出格式

```markdown
# 证书使用场景测试结果

> 扫描范围：仅当前目录

## 发现汇总
| 序号 | 文件 | 维度 | 行号 | 风险 | 描述 |
|------|------|------|------|------|------|

## 统计摘要
| 风险等级 | 数量 |
|---------|------|

## 总结
共扫描 N 个文件，发现 M 处证书使用相关问题。
```
