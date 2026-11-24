#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import requests

def search_city(name: str, timeout: float = 10) -> tuple[float, float] | None:
    """返回 (纬度, 经度)；找不到城市返回 None。"""
    resp = requests.get(url='https://geocoding-api.open-meteo.com/v1/search',
                        params={'name': name, 'count': 1, 'language': 'zh'}, timeout=timeout)
    data = resp.json()
    if not data.get('results'):
        return None
    return data['results'][0]['latitude'], data['results'][0]['longitude']

def main()-> int:
    while True:
        raw = input("城市名（q退出）->\n")
        text = raw.strip().lower()
        if text == "":
            print('空输入\n')
            continue

        elif text in ('q', 'exit', 'quit','退出'):
            print('再见')
            return 0

        else:
            data = search_city(text,10)
            if data is None:
                print(f"找不到城市「{text}」，试试英文名或拼音")
                continue
            else:
                lat, lon = data
                print(f"{text} 的坐标：纬度 {lat:.4f}，经度 {lon:.4f}")

if __name__ == "__main__":
    main()