---
name: protocol-audit-v3
description: "[V3非交互版] 网络协议提取白盒审计。非交互单轮模式,仅扫描当前目录文件(不递归子目录),结果写入AI测试结果.md。提取所有网络协议名称和版本。当用户提到协议审计/协议提取/protocol audit/通信协议扫描时触发此skill。"
---

# 网络协议提取审计 (V3)

**执行模式**：非交互单轮，直接执行，不提问不确认。**仅扫描当前工作目录下的文件，不访问子目录。** 结果写入当前目录的 `AI测试结果.md`。

---

## 一、目标协议

应用层 (L7)：HTTP/HTTPS, HTTP/2, HTTP/3, WebSocket/WSS, RTSP, RTP/RTCP, RTMP, SIP, ONVIF, GB/T 28181, mDNS, DNS, NTP, DHCP, SSH, FTP/SFTP, SMTP, MQTT, AMQP, gRPC, GraphQL, SOAP, REST, SSE, WebRTC

传输层 (L4)：TCP, UDP, QUIC, SCTP

网络层 (L3)：IP Multicast (IGMP), IPsec, ICMP

会话层 (L5-L6)：TLS/SSL, DTLS

## 二、检测模式

- URL 字符串: `https://...`, `wss://...`, `mqtt://...`, `rtsp://...`
- 端口常量: 443→HTTPS, 554→RTSP, 1883→MQTT, 5060→SIP, 1935→RTMP
- 知名地址: 239.255.255.250:1900→SSDP, 224.0.0.251→mDNS
- 库导入: `import paho.mqtt.client`→MQTT, `from aiohttp import`→HTTP
- 注解: @GrpcService→gRPC, @WebSocket→WebSocket
- 框架配置: server.port→HTTP, nginx.conf→HTTP
- TLS/cert 配置: caPath, clientCert, tlsVersionMin, certificatePinning
- 依赖声明: "express"→HTTP, "ws"→WebSocket

## 三、排除项（非网络协议）

- 认证: Digest Auth, Basic Auth, OAuth, Bearer Token, JWT
- 哈希: MD5, SHA-1/256/384/512
- 加密: AES, AES-GCM, RSA, ECDSA
- KMS: HUKS, Android Keystore, iOS Keychain
- 数据格式: JSON, XML, YAML, protobuf (除 gRPC), Base64, PEM
- 地址常量: INADDR_ANY, AF_INET, MAC 地址声明
- Crypto API 对象: cryptoFramework.Md, cryptoFramework.Random
- 算法 OID

---

## 四、Subagent 使用

对当前目录下每个源文件（排除 .md 和 AI测试结果.md），启动独立 subagent：

```
你是协议审计 Agent。阅读文件，提取所有网络协议使用。

文件: {FILE_PATH}

查找协议：HTTP/HTTPS/HTTP2/WebSocket/RTSP/RTP/RTMP/SIP/ONVIF/mDNS/DNS/NTP/DHCP/SSH/FTP/MQTT/AMQP/gRPC/GraphQL/TCP/UDP/QUIC/TLS/DTLS等

检测方式：URL串、端口常量、知名地址、库导入、注解、框架配置、TLS配置、依赖声明

对每个协议记录：协议名称、版本（显式代码→框架默认→URL路径→"版本未指定"）、行号、使用场景（一句话）、来源类型（API调用/URL Scheme/常量定义/配置声明/依赖声明/端口推断）

同协议+同版本去重。

排除：认证机制、哈希/加密算法、KMS、数据格式、地址常量

仅注释中提及 → 不记录为正式发现。
不确定 → 标记"存疑项: [name]"

输出格式：
| 行号 | 协议名称 | 协议版本 | 使用场景 | 来源类型 |
若无: "已审查，无代码级协议发现"
```

---

## 五、输出格式

```markdown
# 网络协议提取结果

> 扫描范围：仅当前目录

## 协议发现列表
| 序号 | 文件 | 行号 | 协议名称 | 版本 | 使用场景 | 来源类型 |
|------|------|------|---------|------|---------|---------|

## 按协议分布
| 协议 | 发现数 |
|------|--------|

## 总结
共扫描 N 个文件，发现 M 项协议使用。
```
