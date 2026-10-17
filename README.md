# clash-sub

Clash / mihomo 订阅配置：`clash-sub.yaml`

订阅地址（raw）：

```
https://raw.githubusercontent.com/Cuenireo/clash-sub/main/clash-sub.yaml
```

## 节点

| 名称 | 类型 | 地址 | 认证 |
| --- | --- | --- | --- |
| `TW-TPE-SOCKS5` | socks5 | 202.66.185.142:6688 | 用户名 + 密码 |
| `TW-TPE-HTTP` | http | 202.66.185.142:6688 | 用户名 + 密码 |

同一个端口 `6688` 同时支持 **SOCKS5** 和 **HTTP** 代理，所以给了两个节点做互备；
默认组 `🚀 节点选择` 里 SOCKS5 排第一。
出口 IP 为 `202.66.185.142`（台湾 台北，AS148996 Global Communication Network Limited）。

## 分组与规则

- `🚀 节点选择`（select，手动）：`♻️ 自动选择` → 两个节点 → `DIRECT`
- `♻️ 自动选择`（url-test，300s，测速 `gstatic.com/generate_204`）
- `🐟 漏网之鱼`（select）
- 规则：内网/回环直连 → `cn` 域名直连 → `GEOIP,CN` 直连 → 其余走 `🐟 漏网之鱼`
- DNS：fake-ip + DoH（doh.pub / alidns），开启 `ipv6`

## 修改凭据 / 换成别的代理

编辑 `params.json` 后重新生成：

```bash
pip install pyyaml
python generate.py
```

`params.json` 字段：

| 字段 | 说明 |
| --- | --- |
| `server` / `port` | 代理地址 |
| `username` / `password` | 代理认证信息 |
| `udp` | 是否启用 UDP 转发（SOCKS5 需服务端支持 UDP ASSOCIATE） |
| `nodes` | 节点列表，每项 `{ "name": ..., "type": "socks5" \| "http" }` |
| `skip_cert_verify` | 仅 socks5 节点生效，跳过证书校验 |

改完运行 `python generate.py`，提交推送即可。
