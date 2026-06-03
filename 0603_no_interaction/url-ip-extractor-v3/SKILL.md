---
name: url-ip-extractor-v3
description: "[V3非交互版] 从工程源码和配置文件中提取所有硬编码的URL地址和IP地址。非交互单轮模式,仅扫描当前目录文件(不递归子目录),结果写入AI测试结果.md。当用户提到提取URL/提取IP/网址检视/网络地址审计时触发此skill。"
---

# URL/IP 地址提取 (V3)

**执行模式**：非交互单轮，直接执行，不提问不确认。**仅扫描当前工作目录下的文件，不访问子目录。** 结果写入当前目录的 `AI测试结果.md`。

---

## 一、关注内容

1. 硬编码完整 URL（http://、https://、rtsp://、ws://、wss://、mqtt://、ftp:// 等）
2. 硬编码 IP 地址（IPv4: 192.168.x.x、10.x.x.x；IPv6: fe80::、::1 等）
3. 配置文件中的服务器域名/地址
4. Mock 数据中的 URL/IP
5. 注释中的 URL/IP 地址（标注来源）

## 二、忽略内容

- 工程内部 API 路径（如 /api/v1/ 无 scheme 的相对路径）
- URL 拼接表达式（如 `${baseUrl}${path}`）
- 端口号常量（如 const PORT = 8080）
- IP 字段定义（如 ipv4_ip: string）
- 变量名（deviceIp、hostUrl）
- import 语句中的包引用 URL
- 密码/凭证

## 三、类型标注

| 类型 | 说明 |
|------|------|
| URL常量 | 带 scheme 的完整 URL |
| IP常量 | IPv4/IPv6 地址 |
| 配置URL | 配置文件中的域名/地址 |
| Mock数据 | 测试代码中的 URL/IP |
| 注释URL | 注释中提及的地址 |

---

## 四、Subagent 使用

对当前目录下每个源文件（排除 .md 和 AI测试结果.md），启动独立 subagent：

```
你是 URL/IP 提取 Agent。阅读文件，提取所有硬编码 URL 和 IP 地址。

文件: {FILE_PATH}

关注：http/https/rtsp/ws/ftp 完整 URL、IPv4/IPv6 地址、配置域名、Mock数据、注释中的地址
忽略：API路径(无scheme)、URL拼接表达式、端口常量、IP字段定义、变量名、import包引用
保留：localhost、0.0.0.0、127.0.0.1、example.com

仅记录发现，不提供修复方案。

输出格式：
| 行号 | 内容 | 类型 | 上下文 |
若无: "无发现"
小结: 共发现 N 处 (URL常量 X, IP常量 Y)
```

---

## 五、输出格式

```markdown
# URL/IP 地址提取结果

> 扫描范围：仅当前目录

## 发现列表
| 序号 | 文件 | 行号 | 内容 | 类型 | 上下文 |
|------|------|------|------|------|--------|

## 按类型统计
| 类型 | 数量 |
|------|------|

## 总结
共发现 N 处硬编码 URL/IP 地址。
```
