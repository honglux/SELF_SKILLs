# 随机数函数目录（按语言/平台）

审计时，SubAgent 应在每个文件中搜索以下模式。此目录覆盖常见语言，主 Agent 应在信息收集阶段根据用户项目实际使用的语言选择对应条目下发给 SubAgent。

---

## ArkTS (HarmonyOS)

### CSPRNG（安全，应出现在安全场景）
| 函数 | 搜索模式 |
|------|---------|
| `cryptoFramework.createRandom()` | `cryptoFramework`, `createRandom` |
| `generateRandom()` / `generateRandomSync()` | `generateRandom` |
| `enableHardwareEntropy()` | `enableHardwareEntropy` |
| `util.generateRandomUUID()` | `generateRandomUUID` |
| `util.generateRandomBinaryUUID()` | `generateRandomBinaryUUID` |

### 不安全（安全场景中为缺陷）
| 函数 | 搜索模式 |
|------|---------|
| `Math.random()` | `Math.random` |
| `Date.now()` | `Date.now` |
| `new Date().getTime()` | `getTime` |
| `performance.now()` | `performance.now` |
| 自定义 PRNG/LCG | 函数名含 `random` 或 `lcg` |

### 上下文关键词
`encrypt`, `decrypt`, `AES`, `SM4`, `GCM`, `CBC`, `IV`, `nonce`, `key`, `cipher`, `token`, `auth`, `cnonce`, `digest`, `session`, `password`, `secret`, `credential`, `challenge`, `salt`, `transaction`, `requestId`, `UUID`, `GUID`

---

## JavaScript / TypeScript (Web/Vue/React/Node.js)

### CSPRNG（安全）
| 函数 | 搜索模式 |
|------|---------|
| `window.crypto.getRandomValues()` | `getRandomValues` |
| `crypto.randomUUID()` | `randomUUID` |
| `crypto.randomBytes()` (Node.js) | `randomBytes` |
| `crypto.randomFill()` (Node.js) | `randomFill` |
| `crypto.generateKey()` (Web Crypto) | `generateKey` |

### 不安全
| 函数 | 搜索模式 |
|------|---------|
| `Math.random()` | `Math.random` |
| `Date.now()` | `Date.now` |
| `new Date().getTime()` | `getTime` |
| `performance.now()` | `performance.now` |
| 自定义 PRNG/LCG | 函数名含 `random` 或 `lcg` |

---

## Java / Kotlin (Android)

### CSPRNG（安全）
| 函数 | 搜索模式 |
|------|---------|
| `java.security.SecureRandom` | `SecureRandom` |
| `SecureRandom.getInstance()` | `SecureRandom` |
| `UUID.randomUUID()` | `randomUUID` |
| `KeyGenerator.getInstance()` | `KeyGenerator` |
| `KeyPairGenerator.getInstance()` | `KeyPairGenerator` |

### 不安全
| 函数 | 搜索模式 |
|------|---------|
| `java.util.Random` | `java.util.Random` 或 `new Random(` |
| `Math.random()` | `Math.random` |
| `ThreadLocalRandom` | `ThreadLocalRandom` |
| `System.currentTimeMillis()` | `currentTimeMillis` |
| 自定义 PRNG/LCG | 自定义 `Random` 子类 |

---

## Python

### CSPRNG（安全）
| 函数 | 搜索模式 |
|------|---------|
| `os.urandom()` | `urandom` |
| `secrets.token_bytes()` | `secrets.token` |
| `secrets.token_hex()` | `secrets.token_hex` |
| `secrets.token_urlsafe()` | `secrets.token_urlsafe` |
| `secrets.choice()` | `secrets.choice` |
| `secrets.randbelow()` | `secrets.randbelow` |
| `ssl.RAND_bytes()` | `RAND_bytes` |
| `uuid.uuid4()` | `uuid4` |

### 不安全
| 函数 | 搜索模式 |
|------|---------|
| `random.random()` | `random.random` 或 `import random` |
| `random.randint()` | `random.randint` |
| `random.choice()` | `random.choice` |
| `numpy.random` | `np.random` 或 `numpy.random` |
| `time.time()` 取低位 | `time.time` |
| `id()` 取低位 | — |

---

## Go

### CSPRNG（安全）
| 函数 | 搜索模式 |
|------|---------|
| `crypto/rand.Read()` | `crypto/rand` 或 `rand.Read` |
| `crypto/rand.Int()` | `rand.Int` (需确认来自 crypto/rand) |
| `crypto/rand.Prime()` | `rand.Prime` |

### 不安全
| 函数 | 搜索模式 |
|------|---------|
| `math/rand.Read()` | `math/rand` |
| `rand.Int()` (math/rand) | — (需检查 import) |
| `rand.Float64()` | `rand.Float64` |
| `time.Now().UnixNano()` 取低位 | — |
| 自定义 PRNG | — |

---

## Rust

### CSPRNG（安全）
| 函数 | 搜索模式 |
|------|---------|
| `rand::rngs::OsRng` | `OsRng` |
| `rand::thread_rng()` (CSPRNG) | `thread_rng` |
| `getrandom::getrandom()` | `getrandom` |

### 不安全
| 函数 | 搜索模式 |
|------|---------|
| `StdRng::from_seed()` (固定种子) | `from_seed` |
| `SmallRng` / `XorShiftRng` | `SmallRng`, `XorShiftRng` |
| 自定义 PRNG | — |
| 时间戳取低位 | — |

---

## C / C++

### CSPRNG（安全）
| 函数 | 搜索模式 |
|------|---------|
| `RAND_bytes()` (OpenSSL) | `RAND_bytes` |
| `RAND_priv_bytes()` (OpenSSL) | `RAND_priv_bytes` |
| `BCryptGenRandom()` (Windows) | `BCryptGenRandom` |
| `getentropy()` (BSD/macOS) | `getentropy` |
| `getrandom()` (Linux) | `getrandom` |
| `/dev/urandom` 读取 | `/dev/urandom` |

### 不安全
| 函数 | 搜索模式 |
|------|---------|
| `rand()` | `rand()` |
| `srand()` | `srand` |
| `random()` (glibc) | `random()` |
| `lrand48()` / `drand48()` | `lrand48`, `drand48` |
| `time()` 取低位 | `time(NULL)` |
| 自定义 LCG / Mersenne Twister | — |

---

## C# / .NET

### CSPRNG（安全）
| 函数 | 搜索模式 |
|------|---------|
| `System.Security.Cryptography.RandomNumberGenerator` | `RandomNumberGenerator` |
| `RNGCryptoServiceProvider` | `RNGCryptoServiceProvider` |
| `Guid.NewGuid()` | `NewGuid` |

### 不安全
| 函数 | 搜索模式 |
|------|---------|
| `System.Random` | `new Random` |
| `Random.Shared` | `Random.Shared` |
| `DateTime.Now` / `DateTime.UtcNow` 取低位 | — |

---

## Swift / Objective-C

### CSPRNG（安全）
| 函数 | 搜索模式 |
|------|---------|
| `SecRandomCopyBytes()` | `SecRandomCopyBytes` |
| `SystemRandomNumberGenerator` | `SystemRandomNumberGenerator` |
| `UUID()` (Foundation) | `UUID()` |

### 不安全
| 函数 | 搜索模式 |
|------|---------|
| `arc4random()` — 注：macOS/iOS 上实际是安全的，但需区分平台 | `arc4random` |
| `random()` | `random()` |
| `drand48()` | `drand48` |
| `GKRandomSource` | `GKRandomSource` |

---

## PHP

### CSPRNG（安全）
| 函数 | 搜索模式 |
|------|---------|
| `random_bytes()` | `random_bytes` |
| `random_int()` | `random_int` |
| `openssl_random_pseudo_bytes()` | `openssl_random_pseudo_bytes` |
| `sodium_randombytes_buf()` | `sodium_randombytes` |

### 不安全
| 函数 | 搜索模式 |
|------|---------|
| `rand()` | `rand()` |
| `mt_rand()` | `mt_rand` |
| `uniqid()` | `uniqid` |
| `lcg_value()` | `lcg_value` |
| `array_rand()` | `array_rand` |
| `shuffle()` | `shuffle` |

---

## Ruby

### CSPRNG（安全）
| 函数 | 搜索模式 |
|------|---------|
| `SecureRandom.hex()` | `SecureRandom` |
| `SecureRandom.random_bytes()` | `SecureRandom` |
| `OpenSSL::Random.random_bytes()` | `OpenSSL::Random` |
| `Securerandom.uuid` | `SecureRandom.uuid` |

### 不安全
| 函数 | 搜索模式 |
|------|---------|
| `rand()` / `Random.rand()` | `rand(` |
| `Random.new` (非 SecureRandom) | `Random.new` |
| `srand()` | `srand` |
| `Array#sample` / `Array#shuffle` | — |

---

## 通用上下文关键词（跨语言）

SubAgent 分析随机数所在上下文时，附近出现以下关键词提示安全敏感：

| 类别 | 关键词 |
|------|--------|
| 加密相关 | `encrypt`, `decrypt`, `AES`, `RSA`, `GCM`, `CBC`, `IV`, `nonce`, `key`, `cipher`, `SM4`, `ChaCha` |
| 认证相关 | `token`, `auth`, `cnonce`, `digest`, `session`, `password`, `secret`, `credential`, `OAuth`, `JWT` |
| 协议相关 | `random`, `challenge`, `nonce`, `transaction`, `requestId`, `salt`, `protocol` |
| 标识相关 | `UUID`, `GUID`, `uniqueId`, `deviceId`, `requestId`, `traceId` |
