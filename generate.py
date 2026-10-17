#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clash-sub generator
===================

把「裸端点清单」转换成 Clash / mihomo 订阅配置。

原始清单每行 7 个字段（无表头）：
    IP:端口,国家,ASN,机房,地区,IPv6地址,备注

用法：
    python generate.py

输入：
    source-endpoints.txt   原始清单（首次运行后可用 endpoints.csv 代替）
    params.json            协议与凭据（必填项见文件内说明）
输出：
    endpoints.csv          规范化端点表
    clash-sub.yaml         Clash / mihomo 订阅配置

依赖：Python 3.8+、PyYAML（pip install pyyaml）
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("缺少依赖 PyYAML，请先执行：pip install pyyaml")

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source-endpoints.txt"
CSV_OUT = ROOT / "endpoints.csv"
YAML_OUT = ROOT / "clash-sub.yaml"
PARAMS = ROOT / "params.json"

CSV_HEADER = ["endpoint", "host", "port", "country", "asn", "provider", "location", "location_code", "city", "ipv6", "note"]
FLAGS = {
    "HK": "🇭🇰", "US": "🇺🇸", "JP": "🇯🇵", "DE": "🇩🇪", "GB": "🇬🇧", "SG": "🇸🇬", "TW": "🇨🇳",
    "KR": "🇰🇷", "NL": "🇳🇱", "FR": "🇫🇷", "CA": "🇨🇦", "AU": "🇦🇺", "RU": "🇷🇺", "TR": "🇹🇷",
}
CN_NAMES = {
    "HK": "香港", "US": "美国", "JP": "日本", "DE": "德国", "GB": "英国", "SG": "新加坡",
    "TW": "台湾", "KR": "韩国", "NL": "荷兰", "FR": "法国", "CA": "加拿大", "AU": "澳大利亚",
    "RU": "俄罗斯", "TR": "土耳其",
}

LOC_RE = re.compile(r"^(?P<code>[A-Za-z0-9]{3,4})\s*[（(]\s*(?P<label>[^)）]*)\s*[)）]\s*$")
LOC_LABEL_RE = re.compile(r"^(?P<country>[^\-－]+)[\-－](?P<city>.+)$")


# --------------------------------------------------------------------------- #
# 解析原始清单
# --------------------------------------------------------------------------- #
def parse_endpoints() -> list[dict]:
    if SOURCE.exists():
        raw_lines = SOURCE.read_text(encoding="utf-8-sig").splitlines()
    elif CSV_OUT.exists():
        with CSV_OUT.open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    else:
        sys.exit(f"找不到输入文件：{SOURCE}")

    rows: list[dict] = []
    for lineno, line in enumerate(raw_lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 7:
            print(f"[warn] 第 {lineno} 行字段数 {len(parts)} != 7，已跳过：{line[:60]}")
            continue
        endpoint, country, asn, provider, location, ipv6, note = parts
        if ":" not in endpoint:
            print(f"[warn] 第 {lineno} 行端点缺少端口，已跳过：{endpoint}")
            continue
        host, _, port = endpoint.rpartition(":")
        host = host.strip("[]")
        if not host or not port.isdigit():
            print(f"[warn] 第 {lineno} 行端点格式异常，已跳过：{endpoint}")
            continue

        code, city, label = country, "", country
        m = LOC_RE.match(location)
        if m:
            code = m.group("code").upper()
            label = m.group("label").strip()
            m2 = LOC_LABEL_RE.match(label)
            city = (m2.group("city") if m2 else label).strip()
        rows.append(
            {
                "endpoint": f"{host}:{port}",
                "host": host,
                "port": port,
                "country": country,
                "asn": asn,
                "provider": provider,
                "location": location,
                "location_code": code,
                "city": city,
                "ipv6": ipv6,
                "note": note,
            }
        )
    if not rows:
        sys.exit("原始清单为空，未解析到任何端点")
    return rows


def write_csv(rows: list[dict]) -> None:
    with CSV_OUT.open("w", encoding="utf-8", newline="\n") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_HEADER, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


# --------------------------------------------------------------------------- #
# 生成节点
# --------------------------------------------------------------------------- #
def load_params() -> dict:
    if not PARAMS.exists():
        sys.exit(f"找不到参数文件：{PARAMS}")
    try:
        params = json.loads(PARAMS.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        sys.exit(f"params.json 解析失败：{exc}")
    params.setdefault("protocol", "vless")
    params.setdefault("uuid", "")
    params.setdefault("password", "")
    params.setdefault("sni", "")
    params.setdefault("host", "")
    params.setdefault("ws_path", "/")
    params.setdefault("tls", True)
    params.setdefault("udp", True)
    params.setdefault("skip_cert_verify", False)
    params.setdefault("use_ipv6", False)
    params.setdefault("client_fingerprint", "chrome")
    params.setdefault("name_prefix", "")
    return params


def build_proxy(row: dict, name: str, params: dict) -> dict:
    protocol = params["protocol"].lower()
    server = row["ipv6"] if params["use_ipv6"] and row.get("ipv6") else row["host"]
    sni = params["sni"].strip()
    host_header = (params["host"] or sni).strip()
    tls = bool(params["tls"])

    proxy: dict = OrderedDict()
    proxy["name"] = name
    proxy["type"] = protocol
    proxy["server"] = server
    proxy["port"] = int(row["port"])

    if protocol == "vless":
        proxy["uuid"] = params["uuid"]
    elif protocol == "vmess":
        proxy["uuid"] = params["uuid"]
        proxy["alterId"] = 0
        proxy["cipher"] = "auto"
    elif protocol == "trojan":
        proxy["password"] = params["password"]
    else:
        sys.exit(f"不支持的 protocol: {protocol}（可选 vless / vmess / trojan）")

    proxy["udp"] = bool(params["udp"])
    proxy["network"] = "ws"
    proxy["tls"] = tls
    if protocol != "trojan":
        proxy["servername"] = sni
    if params["client_fingerprint"]:
        proxy["client-fingerprint"] = params["client_fingerprint"]
    if params["skip_cert_verify"]:
        proxy["skip-cert-verify"] = True

    proxy["ws-opts"] = {"path": params["ws_path"] or "/", "headers": {"Host": host_header}}
    return proxy


def build_config(rows: list[dict], params: dict) -> dict:
    counters: dict[str, int] = {}
    proxies: list[dict] = []
    by_country: dict[str, list[str]] = {}
    for row in rows:
        key = f"{row['country']}-{row['location_code']}"
        counters[key] = counters.get(key, 0) + 1
        name = f"{params['name_prefix']}{key}-{counters[key]:03d}"
        proxies.append(build_proxy(row, name, params))
        by_country.setdefault(row["country"], []).append(name)

    all_names = [p["name"] for p in proxies]

    region_groups: list[dict] = []
    for cc, names in sorted(by_country.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        flag = FLAGS.get(cc, "🌐")
        cn = CN_NAMES.get(cc, cc)
        region_groups.append(
            OrderedDict(
                [
                    ("name", f"{flag} {cn}({cc}) {len(names)}"),
                    ("type", "url-test"),
                    ("proxies", names),
                    ("url", "https://www.gstatic.com/generate_204"),
                    ("interval", 300),
                    ("tolerance", 50),
                    ("lazy", True),
                ]
            )
        )

    groups: list[dict] = [
        OrderedDict(
            [
                ("name", "🚀 节点选择"),
                ("type", "select"),
                (
                    "proxies",
                    ["♻️ 自动选择"] + [g["name"] for g in region_groups] + all_names + ["DIRECT"],
                ),
            ]
        ),
        OrderedDict(
            [
                ("name", "♻️ 自动选择"),
                ("type", "url-test"),
                ("proxies", all_names),
                ("url", "https://www.gstatic.com/generate_204"),
                ("interval", 300),
                ("tolerance", 50),
                ("lazy", True),
            ]
        ),
        *region_groups,
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

    missing = [k for k in ("uuid", "sni") if not params.get(k)]
    if params["protocol"].lower() == "trojan" and not params.get("password"):
        missing.append("password")

    header = [
        "# ============================================================",
        "#  clash-sub  |  mihomo / Clash Meta  订阅配置",
        f"#  节点数：{len(proxies)}    协议：{params['protocol']}  over WS"
        + (" + TLS" if params["tls"] else ""),
        "#  由 generate.py 自动生成，请勿手工修改：改 params.json 后重新运行",
        "# ============================================================",
    ]
    if missing:
        header += [
            "#",
            "#  ⚠️  尚未填写：" + "、".join(missing),
            "#      当前节点里这些字段是占位符（REPLACE_WITH_...），导入后无法连接。",
            "#      编辑 params.json -> 运行 python generate.py 即可重新生成。",
            "#",
        ]

    body = OrderedDict(
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
            ("global-client-fingerprint", "chrome"),
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
                        (
                            "proxy-server-nameserver",
                            ["https://doh.pub/dns-query", "https://dns.alidns.com/dns-query"],
                        ),
                    ]
                ),
            ),
            ("proxies", proxies),
            ("proxy-groups", groups),
            ("rules", rules),
        ]
    )
    return {"header": header, "config": body}


def dump_yaml(result: dict) -> None:
    class _Dumper(yaml.SafeDumper):
        pass

    _Dumper.add_representer(
        OrderedDict, lambda dumper, data: dumper.represent_dict(data.items())
    )
    text = yaml.dump(
        result["config"],
        Dumper=_Dumper,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=4096,
    )
    banner = "\n".join(result["header"]) + "\n\n"
    with YAML_OUT.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(banner + text)


def main() -> None:
    rows = parse_endpoints()
    write_csv(rows)
    params = load_params()
    result = build_config(rows, params)
    dump_yaml(result)
    n = len(result["config"]["proxies"])
    print(f"endpoints : {len(rows)}  ->  {CSV_OUT.name}")
    print(f"proxies   : {n}          ->  {YAML_OUT.name}")
    if params["uuid"] in ("", "REPLACE_WITH_YOUR_UUID"):
        print("提示：params.json 里的 uuid 还是占位符，填好后重新运行本脚本。")


if __name__ == "__main__":
    main()
