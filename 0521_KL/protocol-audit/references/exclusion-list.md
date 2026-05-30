# Protocol Scope Reference — What Counts as a Network Protocol

This reference defines the boundary between "network protocols" (record in results) and
"related but not protocols" (exclude from results). Use this when a subagent is unsure
whether something qualifies.

---

## Network Protocols (INCLUDE)

A network protocol is any specification that governs how data is transmitted, routed,
or session-managed across a network. This maps to OSI layers L3-L7 with network communication
semantics.

### Application Layer (L7)

| Protocol | Common Indicators in Code |
|----------|--------------------------|
| HTTP | `http.createHttp()`, `fetch()`, `XMLHttpRequest`, URLs starting `http://` |
| HTTPS | URLs starting `https://`, TLS-configured HTTP clients, certificate pinning |
| HTTP/2, HTTP/3 | `usingProtocol: HttpProtocol.HTTP2`, `HttpProtocol.HTTP3` |
| WebSocket (WS) | `new WebSocket()`, `webSocket.createWebSocket()`, URLs starting `ws://` |
| WebSocket Secure (WSS) | URLs starting `wss://`, TLS-configured WebSocket |
| RTSP | URLs starting `rtsp://`, RTSP port 554, RTSP client libraries |
| RTP/RTCP | RTP packet handling, RTCP port references |
| RTMP | URLs starting `rtmp://`, RTMP port 1935 |
| SIP | SIP port 5060, SIP message parsing/construction |
| ONVIF | ONVIF service URLs, ONVIF WS-Discovery, ONVIF media profiles |
| GB/T 28181 | SIP-based surveillance protocol, GB28181 device IDs, port 5060 |
| mDNS | `@ohos.net.mdns`, mDNS service discovery, `.local` domains |
| DNS | DNS resolution APIs, DNS-over-HTTPS URLs |
| NTP | NTP server addresses (ntp.xxx.com), NTP port 123 |
| DHCP | DHCP client configuration, DHCP option constants |
| SSH | SSH client libraries, SSH key references, port 22 |
| FTP/SFTP | FTP URLs (`ftp://`), SFTP clients, port 21/22 |
| SMTP | SMTP client config, port 25/587/465 |
| MQTT | MQTT broker URLs (`mqtt://`, `mqtts://`), MQTT topics |
| AMQP | AMQP broker config, RabbitMQ client |
| gRPC | gRPC service definitions, protobuf + HTTP/2 |
| GraphQL | GraphQL endpoint URLs, Apollo client |
| SOAP | SOAP endpoint URLs, WSDL references |
| REST | REST API endpoints (as architectural style over HTTP, record as HTTP/HTTPS with REST path) |
| Server-Sent Events (SSE) | `EventSource()`, `text/event-stream` |
| WebRTC | `RTCPeerConnection`, `RTCDataChannel`, STUN/TURN URLs |

### Transport Layer (L4)

| Protocol | Common Indicators in Code |
|----------|--------------------------|
| TCP | `socket.constructTCPSocketInstance()`, `net.createConnection()`, TCP port references |
| UDP | `socket.constructUDPSocketInstance()`, UDP multicast, UDP send/receive |
| QUIC | QUIC-configured HTTP/3 clients, QUIC libraries |
| SCTP | SCTP socket creation, SCTP port references |

### Network Layer (L3)

| Protocol | Common Indicators in Code |
|----------|--------------------------|
| IP Multicast (IGMP) | `addMembership()`, multicast addresses (224.0.0.0/4), `constructMulticastSocketInstance()` |
| IPsec | VPN configuration, IPsec policy rules |
| ICMP | Ping utilities, ICMP socket creation |

### Session/Presentation Layer (L5-L6)

| Protocol | Common Indicators in Code |
|----------|--------------------------|
| TLS/SSL | `TlsVersion`, `TLSSecureOptions`, `caPath`, `clientCert`, `certificatePinning`, `tlsVersionMin` |
| DTLS | DTLS-configured UDP sockets |

### Custom/Proprietary Protocols

Any project-defined communication protocol that governs data exchange between
system components over a network. Indicators:
- Custom binary packet headers with command type fields
- Project-specific protocol constants (magic numbers, header sizes)
- Custom message framing (length-prefixed, delimiter-based)
- Named protocol: e.g., "SDC Protocol", "HSAPI", "DeviceLink"

---

## NOT Network Protocols (EXCLUDE)

These are related to networking or security but are NOT protocols governing data
transmission or session management. Recording them clutters the results.

### Authentication Schemes

Excluded because they specify HOW to prove identity, not HOW data is transmitted.
- Digest Access Authentication (RFC 2617/7616) — an HTTP auth scheme, not a separate protocol
- Basic Authentication
- OAuth 2.0 / OIDC
- Bearer Token
- API Key authentication
- JWT

*Exception*: If the code implements the full OAuth/OIDC *protocol flow* (redirect, token exchange,
refresh), record "OAuth 2.0" as the protocol since it involves a multi-step network interaction.

### Cryptographic Algorithms (Hash, Encryption, KDF)

Excluded because they process data locally, not transmit it over a network.
- MD5, SHA-1, SHA-256, SHA-384, SHA-512
- AES, AES-GCM, AES-CBC, AES-CTR
- RSA, RSA-OAEP, RSA-PKCS1
- ECDSA, ECDH, Ed25519
- HMAC, HKDF, PBKDF2
- ChaCha20-Poly1305
- 3DES, DES

*Exception*: If the code declares TLS cipher suites (e.g., `TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256`),
record it as part of TLS protocol configuration — the cipher suite is a protocol parameter.

### Cryptographic Infrastructure

Excluded because they are local platform services, not network protocols.
- HUKS (Huawei Universal KeyStore)
- Android Keystore
- iOS Keychain
- PKCS#11
- TPM

### Data Serialization Formats

Excluded because they define data representation, not transmission.
- JSON, JSON5
- XML
- YAML
- ASN.1 DER/BER
- Protocol Buffers (protobuf) — *unless used as gRPC's wire format, in which case record "gRPC"*
- MessagePack, BSON
- Base64, Hex encoding
- PEM (Privacy-Enhanced Mail certificate encoding)

### Address/Interface Constants

Excluded when they merely declare addressing constants without implying a specific protocol.
- `INADDR_ANY` (0.0.0.0) — just means "bind to all interfaces"
- `ADDRESS_FAMILY_IPV4` / `AF_INET` — address family constant
- MAC address declarations — identifier, not protocol
- IP address string constants — without protocol context

*Exception*: If a specific IP is used as a well-known protocol endpoint (e.g., multicast address
239.255.255.250 for SSDP, or 224.0.0.251 for mDNS), record the associated protocol.

### Crypto API Objects

- `cryptoFramework.Md` — message digest API class
- `cryptoFramework.Random` — random number generator API class
- `cryptoFramework.Cipher` — cipher API class

### Algorithm Identifiers (OIDs)

- `OID rsaEncryption` (1.2.840.113549.1.1.1)
- Any other ASN.1 Object Identifier

---

## Edge Cases — Decision Guide

| Item | Verdict | Reason |
|------|---------|--------|
| `DigestAuthClient` class | EXCLUDE as protocol, but NOTE the HTTP context | Digest is auth, not a protocol; the underlying HTTP is the protocol |
| `certificatePinning` config | INCLUDE as TLS feature | It's a TLS security parameter |
| `remoteValidation: 'skip'` | INCLUDE as TLS config | Part of TLS verification strategy |
| `resource://rawfile/certs/ca.pem` | NOTE as TLS cert path | The `resource://` scheme is a local access scheme, not network; but the cert is for TLS |
| `ntp.aliyun.com` string | INCLUDE as NTP | It's an NTP server endpoint |
| Port 443 constant | INCLUDE as HTTPS indicator | Well-known port for a network protocol |
| Port 5060 constant | INCLUDE as SIP | Well-known port for a network protocol |
| SSDP (multicast 239.255.255.250:1900) | INCLUDE as SSDP | Service discovery protocol |
| `ws://` or `wss://` URL | INCLUDE as WebSocket/WSS | Clear protocol scheme |
| `file://` URL | EXCLUDE | Local file access, not network |
| `content://` URI | EXCLUDE | Android content provider, not network |
| `data:` URI | EXCLUDE | Inline data, not network |
| `resource://` scheme | EXCLUDE | HarmonyOS local resource access, not network |
| `rawfile://` scheme | EXCLUDE | HarmonyOS raw file access, not network |
| WiFi (IEEE 802.11) | EXCLUDE | Link layer (L2), too low-level for protocol audit scope; record only if Wi-Fi Direct / WPA3-EAP authentication protocol is explicitly used |
| USB RNDIS / CDC ECM | EXCLUDE | USB device class / hardware interface, not a network protocol; the IP-over-USB tunnel uses standard IP, the RNDIS is just the USB transport |
| Ethernet (IEEE 802.3) | EXCLUDE | Link layer (L2), same reasoning as WiFi |
| HTTP Cookie mechanism (RFC 6265) | EXCLUDE | Part of HTTP state management, not a separate protocol; more like a sub-feature of HTTP |
| REST API version (`/v1/`, `/v2/`) | EXCLUDE | API versioning scheme, not a protocol version; the protocol is HTTP/HTTPS |
| Access-Token / API-Key in headers | EXCLUDE | Authentication mechanism inside HTTP, not a separate protocol |
| UTF-8 text encoding | EXCLUDE | Character encoding, not a network protocol |
| `window.onNativeEvent` / `bridge.invoke` | EXCLUDE (but NOTE the context) | These are JSBridge/WebView IPC mechanisms internal to the app; if they wrap network calls, record the underlying network protocol (HTTP, WebSocket), not the bridge itself |
| `@kit.NetworkKit` / `@kit.RemoteCommunicationKit` | EXCLUDE as protocol, NOTE as framework | These are HarmonyOS SDK kit names — they provide access to protocols but are not protocols themselves |
| IPv4 / IPv6 address family constants | EXCLUDE when used as `family: 1` (bind address) | Address family selection, not a protocol declaration; record the associated protocol (UDP, TCP) instead |
| DHCP (when only inferred from IP assignment) | EXCLUDE without explicit code evidence | DHCP is a protocol, but "the device got an IP somehow" is not evidence. Only record if DHCP client code, DHCP option constants, or DHCP server config is present |
| `loopback` / `127.0.0.1` / `localhost` | EXCLUDE | Loopback is an interface, not a protocol; localhost communication uses whatever protocol the code specifies (HTTP, gRPC, etc.) — record that protocol |
| `setLoopbackMode(false)` | EXCLUDE | Socket configuration option, not a protocol declaration |
