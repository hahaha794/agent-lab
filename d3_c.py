#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import requests
import argparse
import sys

class WeatherError(Exception):
    """本模块所有错误的基类。"""

class CityNotFound(WeatherError):
    """城市名查不到。"""

class NetworkError(WeatherError):
    """连不上网络。"""

class UpstreamError(WeatherError):
    """服务器返回了错误状态。"""
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status

DEFAULT_URL = "https://geocoding-api.open-meteo.com/v1/search"

def lookup_city(name: str,timeout: float = 10, url: str = DEFAULT_URL) ->  tuple[float, float]:
    """返回坐标"""
    try:
        resp = requests.get(url=url,
                        params={'name': name, 'count': 1, 'language': 'zh'}, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if data.get('results'):
            lat,lon = data['results'][0]['latitude'], data['results'][0]['longitude']
            return lat, lon
        else:
            text = f"找不到城市{name}，试试英文名或拼音"
            raise CityNotFound(text)
    except requests.HTTPError as e:
        raise UpstreamError(e.response.status_code, e.response.text) from e
    except requests.Timeout as e:
        raise NetworkError('请求超时') from e
    except requests.ConnectionError as e:
        raise NetworkError('连不上网络') from e
    except requests.JSONDecodeError as e:
        raise UpstreamError(0, '返回内容不是合法Json') from e

def run_once(city: str, url: str = DEFAULT_URL) -> int:
    try:
        lat, lon = lookup_city(city, timeout=10, url=url)
        print(f"{city} 的坐标：纬度 {lat:.4f}，经度 {lon:.4f}")
        return 0
    except CityNotFound:
        print(f"找不到城市「{city}」")
        return 2
    except NetworkError as e:
        print(f"网络错误：{e}")
        return 3
    except UpstreamError as e:
        print(f"服务返回 {e.status}，请稍后再试")
        return 3

def interactive(url: str = DEFAULT_URL) -> int|None:
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
        try:
            lat, lon = lookup_city(name)
            print(f"{name} 的坐标：{lat:.4f}, {lon:.4f}")
        except CityNotFound:
            print(f"找不到城市「{name}」")
            continue
        except NetworkError as e:
            print(f"网络错误：{e}")
            continue
        except UpstreamError as e:
            print(f"服务返回 {e.status}，请稍后再试")
            continue

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