#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import requests
import argparse
import sys
from enum import Enum

class Lookup(Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    ERROR = "error"

EXIT_CODES = {
    Lookup.FOUND: 0,
    Lookup.NOT_FOUND: 2,
    Lookup.ERROR: 3,
}

DEFAULT_URL = "https://geocoding-api.open-meteo.com/v1/search"

def lookup_city(name: str,timeout: float = 10, url: str = DEFAULT_URL) -> tuple[Lookup, tuple[float, float] | None, str]:
    """返回 (状态, 坐标, 给人看的话)。"""
    try:
        resp = requests.get(url=url,
                        params={'name': name, 'count': 1, 'language': 'zh'}, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if data.get('results'):
            lat,lon = data['results'][0]['latitude'], data['results'][0]['longitude']
            text = f"{name} 的坐标：纬度 {lat:.4f}，经度 {lon:.4f}"
            return Lookup.FOUND, (lat, lon), text
        else:
            text = f"找不到城市{name}，试试英文名或拼音"
            return Lookup.NOT_FOUND, None, text
    except requests.HTTPError as e:
        text = e.response.text
        return Lookup.ERROR, None, text
    except requests.Timeout as e:
        return Lookup.ERROR, None, "超时"
    except requests.ConnectionError as e:
        return Lookup.ERROR, None, "网络连接错误"

def run_once(city: str, url: str = DEFAULT_URL) -> int:
    status, coord, message = lookup_city(city, timeout=10, url=url)
    print(message)
    return EXIT_CODES[status]

def interactive(url: str = DEFAULT_URL) -> int:
    """交互模式：反复查询城市坐标，输入 q 退出。返回进程退出码。"""
    while True:
        # 1) 读输入（EOF / Ctrl+C 也算正常退出）
        try:
            raw = input("城市名（q 退出）> ")
        except (EOFError, KeyboardInterrupt):
            print("\n再见")
            return 0

        name = raw.strip()

        # 2) 空输入：提示一下，不发请求
        if not name:
            print("输入不能为空")
            continue

        # 3) 退出
        if name.lower() in {"q", "quit", "exit", "退出"}:
            print("再见")
            return 0

        # 4) 正常查询：只打印，不 return（否则查一次就退出了）
        status, coords, message = lookup_city(name, timeout=10, url=url)
        print(message)

        # 5) 可选：对"找不到"多给一句提示
        if status is Lookup.NOT_FOUND:
            print("（试试英文名或拼音）")

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='查询城市坐标')
    parser.add_argument('city', nargs="?",help='城市名，不传则进入交互模式')
    parser.add_argument('--url', default=DEFAULT_URL,
                        help='接口地址（默认 open-meteo；调试时可指向别的地址）')
    args = parser.parse_args(argv)

    if args.city:
        return run_once(args.city, args.url)
    else:
        return interactive(args.url)


if __name__ == "__main__":
    sys.exit(main())