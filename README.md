# clash-sub

把一份「裸端点清单」转换成 **Clash / mihomo** 订阅配置，并按地区自动分组。

## 文件说明

| 文件 | 作用 |
| --- | --- |
| `source-endpoints.txt` | 原始清单，每行 `IP:端口,国家,ASN,机房,地区,IPv6地址,备注` |
| `endpoints.csv` | 由脚本规范化后的端点表（带表头，含 `仅IPv4` / `仅IPv6` 标记） |
| `params.json` | 节点协议与凭据（**必填项在这里**） |
| `generate.py` | 生成脚本 |
| `clash-sub.yaml` | 生成结果，即交给 Clash 客户端导入的订阅文件 |

## ⚠️ 关于可用性（重要）

原始清单里只有 **IP、端口、国家、ASN、机房、IPv6、仅v4/v6 备注**，
**没有任何身份凭据**：没有 UUID / 密码、没有协议、没有 SNI（伪装域名）、没有 WS path。

节点必须靠这几项才能完成握手，所以：

- `clash-sub.yaml` 的 **613 个节点结构、命名、分组、规则均已就绪**；
- 但凭据字段目前是占位符 `REPLACE_WITH_...`，**直接导入无法连上**；
- 把 UUID / SNI（必要时加 path）填进 `params.json`，重新跑一次脚本即为可用订阅。

## 使用

```bash
pip install pyyaml
# 1. 编辑 params.json：protocol / uuid（或 password）/ sni / ws_path
# 2. 重新生成
python generate.py
```

然后把 `clash-sub.yaml` 导入 Clash Verge / mihomo / ClashX Meta，或用 raw 链接当订阅地址：

```
https://raw.githubusercontent.com/Cuenireo/clash-sub/main/clash-sub.yaml
```

## 生成结果

- 节点：613 个，命名 `国家-机场代码-序号`，例如 `US-LAX-001`、`HK-HKG-007`
- 分组：
  - `🚀 节点选择`（手动）
  - `♻️ 自动选择`（url-test，全部节点）
  - `🇺🇸 美国(US) 582` / `🇭🇰 香港(HK) 27` / `🇯🇵 日本(JP) 3` / `🇩🇪 德国(DE) 1`（url-test，按地区）
  - `🐟 漏网之鱼`
- DNS：fake-ip + DoH（doh.pub / alidns），`ipv6: true`
- 规则：内网直连 / `cn` 域名直连 / `GEOIP,CN` 直连 / 其余走代理

## 换成其它协议

`params.json` 的 `protocol` 支持 `vless`、`vmess`、`trojan`，均为 WS（+TLS）传输：

- `vless` / `vmess` → 需要 `uuid`
- `trojan` → 需要 `password`（无需 `servername`，TLS 用 `sni` 作为 Host）

若实际是 Reality / gRPC / Hysteria2 等，需要改动 `generate.py` 里 `build_proxy()` 的字段，按同样思路扩展即可。
