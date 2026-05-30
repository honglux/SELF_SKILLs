---
name: protocol-audit
description: >
  White-box static analysis skill for extracting all network protocol names and versions
  from source code and configuration files in any project. Use this skill when the user
  asks to audit network protocols, extract protocol usage, scan code for protocols,
  identify communication protocols, find what network protocols a project uses, perform
  protocol inventory, or analyze protocol dependencies. Supports any programming language.
---

# Protocol Audit — Network Protocol Extraction

## Workflow Overview

This skill follows a 4-phase workflow designed to prevent context overflow and ensure complete project coverage:

```
Phase 1: Ask & Confirm   →  Gather root directory, file types, exclusions → write phase1_confirmation.md
Phase 2: Write Plan      →  Explore directory, generate per-file test plan with priority groups
Phase 3: User Approval   →  Present the plan, get confirmation before executing
Phase 4: Execute         →  One subagent per file, save results incrementally
```

**Never skip phases.** Each phase gates the next. Every phase produces a durable artifact on disk so behavior is verifiable and resumable.

---

## Phase 1: Gather Requirements

### Before Asking Questions

**Check path existence first.** Use `ls` (or `Get-ChildItem` on Windows) to verify the root directory exists:

```
If the directory DOES exist → proceed to ask questions normally.
If the directory DOES NOT exist → tell the user clearly: "路径 `{path}` 不存在。请确认正确的项目根目录路径。" Do NOT proceed until the user provides a valid path.
```

### Question Flow

Ask one question at a time. **However, if the user's initial request already specifies all required information (root directory, file types, exclusions), skip the Q&A and jump directly to "Confirm Scope Summary"** — don't make the user repeat themselves.

#### Required Questions

1. **Root directory**: "Which directory should I scan? I'll recursively scan all matching files under this path."

2. **File types to include**: "Which file types should I scan? Options:
   - **Auto-detect**: I'll explore the directory and propose file types based on what I find (recommended for unfamiliar projects)
   - **Default set**: All common source/config types (`.ets`, `.ts`, `.js`, `.vue`, `.jsx`, `.tsx`, `.py`, `.go`, `.java`, `.kt`, `.c`, `.cpp`, `.h`, `.rb`, `.php`, `.swift`, `.rs`, `.json`, `.json5`, `.yaml`, `.yml`, `.env`, `.xml`, `.toml`, `.properties`, `.conf`, `.cfg`, `.ini`, `.gradle`, `.proto`)
   - **Custom set**: you specify specific extensions"

3. **Exclusions**: "Any directories or files to exclude? Common defaults: `node_modules`, `.git`, `dist`, `build`, `target`, `__pycache__`, `*.md` (documentation excluded because they are not source code or config), `rawfile`, `assets`, `vendor`, `.venv`, `venv`."

4. **Language/framework context** (ask even if seemingly obvious — it shapes the test plan's protocol hints):
   "What programming languages or frameworks does this project use? This helps me write more relevant protocol detection guidance. For example: a Python IoT project should look for `paho-mqtt`, `aiohttp`, `aiocoap`; a Go microservice should look for `net/http`, `grpc-go`; an Android app should look for `okhttp`, `retrofit`."

### Confirm Scope Summary

After collecting answers, present a one-paragraph summary and **write it to `phase1_confirmation.md`** at the plan output location:

```
## Phase 1 确认 — 扫描范围

- **根目录**: {root_directory}（{存在/不存在警告}）
- **文件类型**: {extensions}
- **排除项**: {exclusions}
- **语言/框架**: {languages}
- **确认时间**: {timestamp}
```

Ask: "Does this look right? I'll save this as `phase1_confirmation.md` and then write a detailed test plan for your review."

This file serves as:
- A durable reference for later phases (so the executing agent knows exactly what was agreed)
- Verifiable evidence that Phase 1 was completed (important for audits/evaluations)
- A resume point if the session is interrupted

---

## Phase 2: Write the Test Plan

Once the user confirms the scope, explore the directory structure and generate a test plan. Read `references/plan-template.md` for the full template.

### Directory Exploration (Concrete Commands)

Use these exact commands to explore before writing the plan. This ensures consistent discovery regardless of the agent:

**Windows (PowerShell)**:
```powershell
# Count files by extension
Get-ChildItem -LiteralPath "{root}" -Recurse -Include {ext_array} -Exclude {excl_array} | Group-Object Extension | Select-Object Count, Name | Sort-Object Count -Descending

# List subdirectories (for grouping)
Get-ChildItem -LiteralPath "{root}" -Directory -Recurse -Depth 2 | Select-Object FullName

# Check for dependency files
Get-ChildItem -LiteralPath "{root}" -Recurse -Include "package.json","go.mod","pom.xml","build.gradle*","requirements.txt","Cargo.toml","CMakeLists.txt","Podfile" -Exclude "node_modules",".git","dist","build"
```

**Linux/macOS (Bash)**:
```bash
# Count files by extension
find "{root}" -type f \( -name "*{ext1}" -o -name "*{ext2}" ... \) ! -path "*/{excl1}/*" | sed 's/.*\.//' | sort | uniq -c | sort -rn

# List subdirectories
find "{root}" -maxdepth 3 -type d ! -path "*/node_modules/*" ! -path "*/.git/*" | sort

# Check for dependency files
find "{root}" -maxdepth 3 -type f \( -name "package.json" -o -name "go.mod" -o -name "pom.xml" -o -name "build.gradle*" -o -name "requirements.txt" -o -name "Cargo.toml" \) ! -path "*/node_modules/*"
```

### Group Files by Protocol Density

Organize files into priority groups (P0 through PN) based on expected protocol density:

| Priority | Criteria | Group Size |
|----------|----------|------------|
| P0 | Network layer code (HTTP clients, sockets, TLS, DNS, MQTT, WebSocket) | ≤ 15 files |
| P1 | Security/crypto code (certificates, key stores, TLS config) | ≤ 15 files |
| P2 | Service/API layer (REST clients, RPC handlers, GraphQL, gRPC stubs) | ≤ 20 files |
| P3 | Bridge/middleware layer (JSBridge, IPC, message queues) | ≤ 25 files |
| P4 | Configuration files (.yaml, .json, .env, .properties, .xml, .toml, .gradle) | ≤ 25 files |
| P5 | Dependency manifests (package.json, go.mod, pom.xml, requirements.txt) | ≤ 15 files |
| P6+ | UI, models, utils, storage, etc. (descending priority, one group per module) | ≤ 38 files |

**Critical rule**: No group may exceed 38 files. If a category has more files, split it into sub-groups (e.g., P6a-models, P6b-utils). Large groups tempt the executing agent to batch-skip files.

### Plan Must Include

1. **Scope reference** — link to `phase1_confirmation.md`
2. **Per-file checklist** with exact file paths (from directory exploration, not glob guesses)
3. **Protocol detection hints** tailored to each group's language/framework
4. **Dependency file protocol hints** — what to look for in package.json (library names like `express`, `axios` imply HTTP; `ws` implies WebSocket; `mqtt` implies MQTT), go.mod, requirements.txt, pom.xml, etc.
5. **Config file protocol hints** — URL patterns, port numbers, TLS settings, broker addresses, endpoint definitions
6. **Exclusion list** clearly stated (reference `references/exclusion-list.md`)
7. **All execution rules** from Phase 4 below
8. **Output file path** where results will be saved
9. **Cross-file variable tracing note**: when a file references a protocol-related variable defined externally (like `PHOConstants.PHO_BASE_URL`), the subagent must note it as "变量追溯失败: <variable>" — the main agent will then verify whether the defining file is also in the scan scope

### Plan Document Location

Write the plan to `{root_directory}/TestPlan/ProtocolTest/Protocol_Extraction_Test_Plan.md`.

**If the root directory does not exist**: write the plan to the current working directory or a user-specified path, and note in the plan that the root path needs verification before execution.

Also save `phase1_confirmation.md` to the same directory.

---

## Phase 3: User Review

Present the completed plan with a summary:

- Total files to scan (count by group)
- Number of priority groups
- Estimated execution time (~15-30s per file due to subagent overhead)
- Output file path
- Link to the written plan file

Ask explicitly: "Does this plan look good? I'll start executing once you confirm. You can ask me to adjust: add/remove files, reorder groups, change output paths, etc."

**Do not proceed to Phase 4 without explicit user confirmation.**

---

## Phase 4: Execute Tests

This is where the actual protocol extraction happens. Follow these rules without exception.

### 4.1 Per-File Subagent Strategy

For each file in the plan, spawn a **dedicated subagent** with its own context:

1. Main agent reads `phase1_confirmation.md` and the test plan to know what to do
2. Main agent reads the next untested file from the plan
3. Main agent spawns a subagent to read the full file and extract protocols
4. Subagent returns structured findings to main agent
5. Main agent **appends results to the output file immediately** (do not batch in memory)
6. Main agent releases the subagent and moves to the next file

**This is the core strategy to prevent context overflow.** A subagent that reads one file uses minimal context. If all files were read in the main context, it would overflow after 10-15 files.

**For dependency files** (package.json, go.mod, pom.xml, requirements.txt, build.gradle, Cargo.toml, CMakeLists.txt): the main agent reads these directly (they are small) and extracts protocol-relevant library names. No subagent needed for these files. Record findings like: "MQTT — paho-mqtt 1.6.1（依赖声明）", "gRPC — grpc-go v1.60（依赖声明）".

### 4.2 Subagent Prompt Template

Each subagent receives this prompt. The exclusion list is referenced via the reference file — the main agent should include the key exclusion categories inline for the subagent's convenience (subagents cannot read the skill's reference files):

```
Read this file and extract all network protocol usage.

File: {absolute_file_path}
Language: {detected_language}

A "network protocol" governs how data is transmitted, routed, or session-managed
across a network (OSI L3-L7). Key protocols to look for:

Application (L7): HTTP/HTTPS, HTTP/2, HTTP/3, WebSocket/WSS, RTSP, RTP/RTCP,
  RTMP, SIP, ONVIF, GB/T 28181, mDNS, DNS, NTP, DHCP, SSH, FTP/SFTP, SMTP,
  MQTT, AMQP, gRPC, GraphQL, SOAP, REST, SSE, WebRTC
Transport (L4): TCP, UDP, QUIC, SCTP
Network (L3): IP Multicast (IGMP), IPsec, ICMP
Session (L5-L6): TLS/SSL, DTLS
Custom: any project-defined binary/text protocol with command types, magic numbers,
  header structures, or message framing

Protocol detection patterns (beyond API calls):
- URL strings: https://..., wss://..., mqtt://..., rtsp://..., rtmp://...
- Port constants: 443 → HTTPS, 554 → RTSP, 1883 → MQTT, 5060 → SIP, 1935 → RTMP
- Well-known addresses: 239.255.255.250:1900 → SSDP, 224.0.0.251 → mDNS
- Library imports: import paho.mqtt.client → MQTT, from aiohttp import → HTTP
- Annotations: @GrpcService → gRPC, @WebSocket → WebSocket
- Framework config: server.port (Spring Boot → HTTP), nginx.conf → HTTP
- TLS/cert config: caPath, clientCert, tlsVersionMin, certificatePinning, ssl_context
- Dependency declarations: "express": "^4.18" → HTTP, "ws": "^8.0" → WebSocket

EXCLUDE (not network protocols — these process data locally or identify entities,
not govern network transmission):
- Authentication: Digest Auth, Basic Auth, OAuth, Bearer Token, JWT, API Key
- Hash: MD5, SHA-1/256/384/512
- Encryption: AES, AES-GCM, RSA, ECDSA, ChaCha20
- KMS: HUKS, Android Keystore, iOS Keychain
- Data formats: JSON, XML, YAML, ASN.1 DER, protobuf (unless as gRPC wire format), Base64, PEM
- Address constants: INADDR_ANY, AF_INET, MAC address declarations
- Crypto API objects: cryptoFramework.Md, cryptoFramework.Random
- Algorithm OIDs

For each protocol found, record:
1. Protocol name
2. Version (inference priority: explicit code → framework default → URL path → "版本未指定" — never leave blank)
3. Line number
4. What the code is doing (one sentence in Chinese)
5. Source type: API调用 / URL Scheme / 常量定义 / 配置声明 / 变量追溯 / 依赖声明 / 端口推断

Same protocol + same version → only record once per file (deduplicate).

If the protocol value is in a variable defined outside this file, mark as
"变量追溯失败: <variable_name>" with the variable path.

Protocol references ONLY in comments → do NOT record as formal findings.
If ALL protocol references are from comments → return "已审查，无代码级协议发现".

If something MIGHT be a protocol but you're unsure → mark "存疑项: [name]"
with full code context for the main agent to verify.

Config files (.yaml, .json, .env, .properties, .xml, .toml):
- Look for URL/endpoint keys: base_url, api_endpoint, server, host, broker, mqtt_url
- Look for port keys: port, http_port, https_port, mqtt_port
- Look for TLS/SSL keys: ssl, tls, cert, certificate, ca_path
- Look for protocol scheme prefixes in values: http://, https://, mqtt://, grpc://

Output format (one row per finding):
| 行号 | 协议名称 | 协议版本 | 使用场景 | 来源类型 |

If no protocols found:
| — | — | — | 已审查，无协议发现 | — |

For dependency files, output:
| — | {protocol} | {version_from_dep} | {library_name} 依赖声明 | 依赖声明 |
```

### 4.3 Anti-Batch Rule

**Never batch-summarize multiple files into one entry.** This was the #1 failure mode in testing. Even if 50 component files seem "unlikely to contain protocols," each must have its own entry. Wrong:

```
| components/*.vue | — | — | — | 已批量审查 | — |
```

Correct — every file gets its own entry:
```
#### components/Dialog.vue
| — | — | — | 已审查，无协议发现 | — |

#### components/List.vue
| — | — | — | 已审查，无协议发现 | — |
```

### 4.4 Progress Checkpoints

After completing each priority group, pause and verify all four checks:

1. **Count check**: Completed files = planned files for this group? If N < planned, list which files were missed.
2. **Format check**: Every file has its own entry (no batch summaries like `components/*.vue`)?
3. **Duplicate check**: No file appears twice in results (check by file path)?
4. **Save check**: All results for this group actually written to disk (verify file size increased)?

**Write a checkpoint summary** at the end of the group's results:
```
> 进度检查点 P0: 15/15 完成 ✓ | 格式 ✓ | 去重 ✓ | 已落盘 ✓
```

Only proceed to the next group if all four checks pass. If any check fails, fix the issue before continuing.

### 4.5 Uncertain Items Protocol

If a subagent returns a `存疑项`:

1. Main agent spawns a **new dedicated subagent** specifically to verify that item
2. The verification subagent reads the original file and surrounding context (adjacent files, configs)
3. If confirmed as a protocol → add to results with full details
4. If confirmed not a protocol → discard with a brief note why
5. If still uncertain after verification → add with note "⚠ 需人工确认: [context and reasoning]"

The uncertain item should NOT block progress on other files — continue scanning while the verification subagent runs.

### 4.6 Cross-File Variable Resolution

When a subagent reports "变量追溯失败: <variable>":

1. Check if the defining file is in the scan scope
2. If yes → when that file's turn comes, the subagent should resolve the variable value
3. If the defining file has already been scanned → re-check its results for the variable value, update the original entry
4. If the defining file is outside the scan scope → mark as "变量追溯失败: <variable>（定义文件不在扫描范围内）"

This ensures protocol URLs defined in config/constants files are properly resolved even when they appear in code as imported variables.

### 4.7 Resume Capability

The append-only output format naturally supports resume. If execution is interrupted:
1. Read the output file to find the last completed checkpoint (look for `> 进度检查点`)
2. Resume from the next uncompleted group
3. No need to re-scan already-checkpointed groups

The `phase1_confirmation.md` and test plan files on disk also serve as resume anchors.

### 4.8 Results File

Save results to the path specified in the test plan (typically `{root_directory}/TestPlan/ProtocolTest/Protocol_Extraction_Results.md`).

After all files are tested, append a global summary section:

1. **By protocol name** — which protocols found, in how many files, which files
2. **By module** — how many files tested per module, how many had protocol findings
3. **No-finding files list** — every file that was scanned but had no protocols, with a brief reason
4. **Version inference notes** — explain which versions were explicit, inferred from defaults, or unassigned
5. **Uncertain items** — collect all "需人工确认" items for reviewer attention

---

## Reference Files

- `references/exclusion-list.md` — Detailed list of what IS and IS NOT a network protocol, with 35+ edge case decisions. **Always reference this when uncertain.**
- `references/plan-template.md` — Full test plan document template used in Phase 2
