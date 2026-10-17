#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clash-sub generator
===================

读取 params.json，生成 Clash / mihomo 订阅配置 clash-sub.yaml。

用法：
    python generate.py

依赖：Python 3.8+、PyYAML（pip install pyyaml）
"""

from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("缺少依赖 PyYAML，请先执行：pip install pyyaml")

ROOT = Path(__file__).resolve().parent
PARAMS = ROOT / "params.json"
YAML_OUT = ROOT / "clash-sub.yaml"

TEST_URL = "https://www.gstatic.com/generate_204"


def load_params() -> dict:
    if not PARAMS.exists():
        sys.exit(f"找不到参数文件：{PARAMS}")
    try:
        params = json.loads(PARAMS.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        sys.exit(f"params.json 解析失败：{exc}")

    for key in ("server", "port", "username", "password"):
        if not params.get(key):
            sys.exit(f"params.json 缺少必填字段：{key}")
    params.setdefault("nodes", [{"name": "节点", "type": "socks5"}])
    params.setdefault("udp", True)
    params.setdefault("skip_cert_verify", False)
    params.setdefault("tag", "")
    return params


def build_proxy(params: dict, node: dict) -> OrderedDict:
    kind = str(node.get("type", "socks5")).lower()
    if kind not in ("socks5", "http"):
        sys.exit(f"不支持的节点类型：{kind}（可选 socks5 / http）")

    proxy = OrderedDict()
    proxy["name"] = node.get("name") or f"{kind}-{params['server']}"
    proxy["type"] = kind
    proxy["server"] = params["server"]
    proxy["port"] = int(params["port"])
    proxy["username"] = params["username"]
    proxy["password"] = params["password"]
    proxy["udp"] = bool(params["udp"]) and kind == "socks5"
    if kind == "socks5" and params["skip_cert_verify"]:
        proxy["skip-cert-verify"] = True
    return proxy


def build_config(params: dict) -> OrderedDict:
    proxies = [build_proxy(params, node) for node in params["nodes"]]
    names = [p["name"] for p in proxies]

    groups = [
        OrderedDict(
            [
                ("name", "🚀 节点选择"),
                ("type", "select"),
                ("proxies", ["♻️ 自动选择"] + names + ["DIRECT"]),
            ]
        ),
        OrderedDict(
            [
                ("name", "♻️ 自动选择"),
                ("type", "url-test"),
                ("proxies", names),
                ("url", TEST_URL),
                ("interval", 300),
                ("tolerance", 50),
                ("lazy", True),
            ]
        ),
        OrderedDict(
            [
                ("name", "🐟 漏网之鱼"),
                ("type", "select"),
                ("proxies", ["🚀 节点选择", "♻️ 自动选择", "DIRECT"]),
            ]
        ),
    ]

    rules = [
        "DOMAIN-SUFFIX,local,DIRECT",
        "IP-CIDR,127.0.0.0/8,DIRECT,no-resolve",
        "IP-CIDR,10.0.0.0/8,DIRECT,no-resolve",
        "IP-CIDR,172.16.0.0/12,DIRECT,no-resolve",
        "IP-CIDR,192.168.0.0/16,DIRECT,no-resolve",
        "IP-CIDR,100.64.0.0/10,DIRECT,no-resolve",
        "DOMAIN-SUFFIX,cn,DIRECT",
        "GEOIP,CN,DIRECT",
        "MATCH,🐟 漏网之鱼",
    ]

    return OrderedDict(
        [
            ("mixed-port", 7890),
            ("allow-lan", False),
            ("bind-address", "*"),
            ("mode", "rule"),
            ("log-level", "info"),
            ("ipv6", True),
            ("external-controller", "127.0.0.1:9090"),
            ("unified-delay", True),
            ("tcp-concurrent", True),
            ("find-process-mode", "strict"),
            ("profile", OrderedDict([("store-selected", True), ("store-fake-ip", True)])),
            (
                "dns",
                OrderedDict(
                    [
                        ("enable", True),
                        ("ipv6", True),
                        ("listen", "0.0.0.0:1053"),
                        ("enhanced-mode", "fake-ip"),
                        ("fake-ip-range", "198.18.0.1/16"),
                        ("fake-ip-filter", ["*.lan", "*.local", "+.msftconnecttest.com", "+.msftncsi.com"]),
                        ("default-nameserver", ["223.5.5.5", "119.29.29.29"]),
                        ("nameserver", ["https://doh.pub/dns-query", "https://dns.alidns.com/dns-query"]),
                    ]
                ),
            ),
            ("proxies", proxies),
            ("proxy-groups", groups),
            ("rules", rules),
        ]
    )


def dump_yaml(config: OrderedDict, params: dict) -> None:
    class _Dumper(yaml.SafeDumper):
        pass

    _Dumper.add_representer(
        OrderedDict, lambda dumper, data: dumper.represent_dict(data.items())
    )

    header = [
        "# ============================================================",
        "#  clash-sub  |  mihomo / Clash Meta  订阅配置",
        f"#  节点：{len(config['proxies'])} 个    {params['server']}:{params['port']}",
        f"#  类型：{'、'.join(p['type'] for p in config['proxies'])}    带用户名/密码认证",
        "#  由 generate.py 自动生成，请勿手工修改：改 params.json 后重新运行",
        "# ============================================================",
        "",
    ]
    text = yaml.dump(
        config,
        Dumper=_Dumper,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=4096,
    )
    with YAML_OUT.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(header) + text)


def main() -> None:
    params = load_params()
    config = build_config(params)
    dump_yaml(config, params)
    print(f"proxies: {len(config['proxies'])}  ->  {YAML_OUT.name}")
    for p in config["proxies"]:
        print(f"  - {p['name']}  ({p['type']}) {p['server']}:{p['port']}")


if __name__ == "__main__":
    main()
