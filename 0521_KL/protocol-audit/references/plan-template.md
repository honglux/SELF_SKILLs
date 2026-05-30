# Test Plan Template

Use this template when generating the test plan in Phase 2. Replace `{placeholders}` with
project-specific values. The plan must be written in Chinese (the executing agent works
better with Chinese instructions).

---

```markdown
# 网络协议名称与版本提取 — 白盒测试计划

> 版本: v1.0
> 创建时间: {YYYY-MM-DD}
> 测试范围: {root_directory}
> 测试目标: 提取所有代码和配置文件中使用的网络协议名称及版本号
> 文件类型: {extensions}
> Phase 1 确认: 见 phase1_confirmation.md

---

## 一、测试概述

以白盒测试员的视角，从源码层面静态审查本工程中所有代码文件和配置文件，
提取使用的网络协议名称和版本号。

### 分析方法

1. 逐文件扫描，识别网络协议 API 调用、URL Scheme、协议常量/枚举、配置声明、端口推断、依赖声明
2. 从 API 参数中提取协议版本号（显式指定 → 框架默认 → URL 路径推断 → 无法确定）
3. 协议方法动态存储在变量中时，追溯变量定义；跨文件变量由主 agent 协调解析
4. 同一文件内相同协议名+版本号仅记录第一次出现
5. 依赖声明文件（package.json、go.mod、pom.xml 等）由主 agent 直接读取提取

---

## 二、测试范围

### 纳入范围

| 模块 | 路径 | 文件数 | 语言 |
|------|------|--------|------|
| {module_name} | {path} | {count} | {lang} |
| ... | ... | ... | ... |

### 排除范围

| 排除项 | 原因 |
|--------|------|
| *.md | 文档文件 |
| node_modules/ | 第三方依赖 |
| .git/ | 版本控制 |
| dist/, build/, target/ | 构建产物 |
| __pycache__/ | Python 缓存 |
| rawfile/ | 非源码资源（HarmonyOS） |
| {custom_exclusions} | {reasons} |

---

## 三、非协议排除清单

以下类别不是网络协议，禁止记录到结果中：

| 类别 | 示例 | 排除原因 |
|------|------|---------|
| 认证方案 | Digest Auth, Basic Auth, OAuth 2.0, Bearer Token, JWT, API Key | 证明身份的方式，非数据传输协议 |
| 哈希算法 | MD5, SHA-1, SHA-256, SHA-384, SHA-512 | 本地数据处理，非网络通信 |
| 加密算法 | AES, AES-GCM, RSA, ECDSA, ChaCha20, 3DES | 本地数据处理，非网络通信 |
| KMS 系统 | HUKS, Android Keystore, iOS Keychain | 本地密钥管理服务 |
| 数据格式 | JSON, XML, YAML, ASN.1 DER, protobuf, Base64, PEM, MessagePack | 数据表示格式，非传输协议 |
| 地址常量 | INADDR_ANY, AF_INET, MAC 地址声明 | 仅声明地址族，非协议 |
| Crypto API 对象 | cryptoFramework.Md, cryptoFramework.Random | API 类声明，非协议 |
| 算法 OID | OID rsaEncryption | ASN.1 对象标识符 |

**特例**：
- OAuth 2.0 如果实现了完整协议流程（redirect → token exchange → refresh）→ 记录为 "OAuth 2.0（协议流程）"
- protobuf 作为 gRPC 的线格式时 → 记录为 "gRPC"
- TLS 密码套件声明（如 TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256）→ 记录为 TLS 协议配置参数
- 知名组播地址（如 239.255.255.250:1900 → SSDP, 224.0.0.251 → mDNS）→ 记录关联协议

---

## 四、测试执行原则

1. **每个文件使用独立 subagent**：避免主 agent 上下文溢出
2. **单文件完成即落盘**：结果追加写入，不等待全部完成
3. **禁止批量汇总**：每个文件必须有独立条目，不允许 `components/*.vue` 批量跳过
4. **进度检查点**：每完成一组后验证四项（数量/格式/去重/落盘），写检查点摘要，不通过不继续
5. **存疑项二次确认**：创建新 subagent 专项确认，不阻塞其他文件扫描
6. **跨文件变量解析**：变量追溯失败时，若定义文件在扫描范围内则后续解析并回填
7. **依赖文件主 agent 直读**：package.json 等由主 agent 直接分析，无需 subagent
8. **仅记录发现，不提供修复方案**

---

## 五、测试分组

| 组别 | 范围 | 文件数 | 预计耗时 |
|------|------|--------|---------|
| P0 | {network_layer} | {count} | ~{est}min |
| P1 | {security_layer} | {count} | ~{est}min |
| P2 | {service_layer} | {count} | ~{est}min |
| P3 | {middleware_layer} | {count} | ~{est}min |
| P4 | {config_files} | {count} | ~{est}min |
| P5 | {dependency_files} | {count} | ~{est}min |
| P6+ | {other_modules} | {count} | ~{est}min |

---

## 六、逐文件测试清单

### P0 — {group_name}（{count} 个文件）

**协议密度**: 高 — 网络通信核心代码
**协议检测重点**: HTTP/HTTPS API 调用、TLS/SSL 配置、Socket 创建、URL Scheme、组播、自定义协议

| 序号 | 文件路径 |
|------|---------|
| P0-01 | {absolute_path} |
| P0-02 | {absolute_path} |
| ... | ... |

---

### P4 — 配置文件（{count} 个文件）

**协议密度**: 中 — 可能包含服务端点、端口、TLS 配置
**协议检测重点**: URL/endpoint 键值、port 声明、SSL/TLS 配置块、broker 地址、scheme 前缀

| 序号 | 文件路径 |
|------|---------|
| P4-01 | {absolute_path} |
| ... | ... |

---

### P5 — 依赖声明文件（{count} 个文件）

**协议密度**: 低 — 间接证据
**分析方法**: 主 agent 直接读取，提取协议相关库名和版本
**协议检测重点**: HTTP 框架（express, axios, aiohttp, okhttp）、MQTT 客户端（paho-mqtt, aio-mqtt）、gRPC（grpc-go, grpcio）、WebSocket（ws, websocket-client）

| 序号 | 文件路径 |
|------|---------|
| P5-01 | {absolute_path}/package.json |
| ... | ... |

---

[重复直到覆盖所有分组]

---

## 七、输出文件

- **Phase 1 确认**: `{output_dir}/phase1_confirmation.md`
- **测试结果**: `{output_dir}/Protocol_Extraction_Results.md`
- **格式**: 每个文件一个独立条目，追加写入
- **完成后生成**:
  1. 按协议名称汇总表
  2. 按模块统计表
  3. 无发现文件列表（含原因）
  4. 版本推断说明
  5. 存疑项汇总

---

## 八、参考资源

- `references/exclusion-list.md` — 完整协议/非协议边界参考手册
- 项目编码规范文档（如 CLAUDE.md）
- 框架协议 API 文档（视语言/框架而定）
```
