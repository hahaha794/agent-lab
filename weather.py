#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys

import weatherapi

def interactive() -> int|None:
    """交互模式：反复查询城市天气，输入 q 退出。返回进程退出码。"""
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
            city_weather = weatherapi.get_weather(name,"celsius")
            print(format_weather(city_weather))
        except weatherapi.CityNotFoundError:
            print(f"找不到城市{name}，请检查写法（支持中文/英文/拼音）")
            continue
        except weatherapi.RetryableError as e:
            print(f"服务暂时不可用（HTTP {e.status}），请稍后再试")
            continue
        except weatherapi.NetworkError as e:
            print(f"网络错误：{e}")
            continue
        except weatherapi.UpstreamError as e:
            print(f"请求失败（HTTP {e.status}）" if e.status else "服务返回了无法解析的内容（可能被网络拦截）")
            continue

def format_weather(w: dict) -> str:
    """把 get_weather 返回的 dict 拼成一行人话。"""
    return (
        f"{w['city']} 现在 {w['temperature']}{w['unit']}"
        f"（体感 {w['feels_like']}{w['unit']}），{w['description']}，"
        f"湿度 {w['humidity']}%，风速 {w['wind_speed']} km/h"
    )

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='查询城市天气')
    parser.add_argument('city', nargs="?",help='城市名（中文/英文/拼音）')
    parser.add_argument("--json",action = "store_true", help = "把结果用JSON格式打印" )
    parser.add_argument("--unit",choices=["celsius", "fahrenheit"],default="celsius",help="温度单位（默认 celsius）",)
    parser.add_argument("--timeout", type=float, default = 10.0,help = "读取超时（秒）" )
    parser.add_argument("--attempts", type = int,default=3,help = "最多尝试次数（429/5xx/网络错误时重试）" )
    parser.add_argument("--url", type = str, default="https://api.open-meteo.com/v1/forecast",help = "调试用（指向假服务器）,只影响经纬度查询" )
    args = parser.parse_args(argv)

    if args.city:
        try:
            city_weather = weatherapi.get_weather(args.city,args.unit,args.url,args.timeout,args.attempts,)
        except weatherapi.CityNotFoundError:
            print(f"找不到城市{args.city}，请检查写法（支持中文/英文/拼音）")
            return 2
        except weatherapi.RetryableError as e:
            print(f"服务暂时不可用（HTTP {e.status}），请稍后再试")
            return 3
        except weatherapi.NetworkError as e:
            print(f"网络错误：{e}")
            return 3
        except weatherapi.UpstreamError as e:
            print(f"请求失败（HTTP {e.status}）" if e.status else "服务返回了无法解析的内容（可能被网络拦截）")
            return 3
        if args.json:
            print(json.dumps(city_weather, ensure_ascii=False, indent=2))
        else:
            print(format_weather(city_weather))
        return 0
    else:
        return interactive()

if __name__ == "__main__":
    sys.exit(main())