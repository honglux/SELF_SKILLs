---
name: crypto-extractor-v3
description: "[V3非交互版] 从工程源码中提取所有加密算法、加密函数和加密相关配置。非交互单轮模式,仅扫描当前目录文件(不递归子目录),结果写入AI测试结果.md。当用户提到提取加密/加密算法检视/加密白盒测试时触发此skill。"
---

# 加密算法提取 (V3)

**执行模式**：非交互单轮，直接执行，不提问不确认。**仅扫描当前工作目录下的文件，不访问子目录。** 结果写入当前目录的 `AI测试结果.md`。

---

## 一、加密关键词清单

### 多语言通用
| 分类 | 关键词 |
|------|--------|
| 编码转换 | Base64, base64, encode, decode, btoa, atob, hex, binary |
| 密钥相关 | password, secret, key, token, nonce, iv, salt, authTag |
| 安全相关 | encrypt, decrypt, hash, cipher, signature, crypto |
| 证书相关 | cert, certificate, x509, ssl, tls, pem, der |

### ArkTS/TS/JS
| 分类 | 关键词 |
|------|--------|
| 模块导入 | cryptoFramework, huks, @kit.CryptoArchitectureKit |
| 消息摘要 | createMd, digest, SHA256, SHA384, SHA512, MD5 |
| 对称加密 | createCipher, createSymKeyGenerator, AES256, AES128, GCM, CBC |
| 非对称加密 | createAsyKeyGenerator, RSA2048, PKCS1, OAEP |
| HUKS | generateKeyItem, initSession, HuksTag, HuksKeyAlg |
| Web Crypto | crypto.subtle, SubtleCrypto, generateKey, deriveKey |
| 密钥派生 | PBKDF2, HKDF, ECDH, importKey, exportKey |

### Java
Cipher, MessageDigest, Mac, Signature, KeyGenerator, KeyPairGenerator, AES, RSA, DES, SHA-256, MD5, HmacSHA256, SecretKey, PublicKey, PrivateKey, KeyStore, SecureRandom

### Python
hashlib, hmac, secrets, cryptography, PyCryptodome, AES, RSA, SHA256, MD5, HMAC, Cipher, PKCS1_OAEP, base64, ssl, certifi, OpenSSL

### Go
crypto/aes, crypto/rsa, crypto/sha256, crypto/hmac, crypto/rand, aes.NewCipher, rsa.GenerateKey, sha256.Sum256, hmac.New, crypto/x509, tls.Config, encoding/base64

### C/C++
EVP_CIPHER_CTX, EVP_aes_256_gcm, EVP_sha256, RSA, HMAC, RSA_public_encrypt, RAND_bytes, X509, SSL_CTX

### Rust
aes, rsa, sha2, hmac, rand, ring, openssl, Aes256Gcm::new, Sha256::digest, rustls, x509-parser

### C#
System.Security.Cryptography, Aes, Rsa, SHA256, MD5, HMACSHA256, RNGCryptoServiceProvider, X509Certificate2, X509Store

---

## 二、Subagent 使用

对当前目录下每个源文件，启动独立 subagent：

```
你是加密提取 Agent。阅读文件，提取所有加密相关代码。

文件: {FILE_PATH}

搜索加密关键词（根据文件语言选取），记录：
- 加密类型：消息摘要|对称加密|非对称加密|HMAC|随机数生成|密钥派生|密钥存储|编码转换
- 具体函数/API名称
- 代码行号
- 使用场景简述
- 上下文：[核心使用] / [模块导入] / [注释提及] / [配置引用]

仅记录发现，不提供修复方案或安全评估。

输出格式：
| 行号 | 加密类型 | 具体API | 使用场景 | 上下文 |
若文件中无加密使用: "无加密使用"
```

---

## 三、输出格式

```markdown
# 加密函数提取测试结果

> 扫描范围：仅当前目录

## 提取结果列表
| 序号 | 文件 | 行号 | 加密类型 | 具体API | 使用场景 | 上下文 |
|------|------|------|---------|--------|---------|--------|

## 加密类型统计
| 加密类型 | 使用次数 |
|---------|---------|

## 总结
共扫描 N 个文件，发现加密使用 M 处。
```
