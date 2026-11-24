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


if __name__ == "__main__":
    print(search_city("北京", timeout=1))