#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import requests

def probe(url: str, params: dict | None = None,timeout: float = 10) -> None:
    """请求并打印结果；4xx/5xx 走异常分支，不许崩。"""
    try:
        resp = requests.get(url, params=params,timeout = timeout)
        resp.raise_for_status()
        print(f"OK:{resp.reason}")
    except requests.HTTPError as e:
        print(f"ERROR:{e.response.status_code}:{e.response.reason}")
    except requests.Timeout as e:
        print(f"ERROR:超时")
    except requests.ConnectionError as e:
        print(f"ERROR:网络连接错误")

def main():
    test_url = [
        ("https://geocoding-api.open-meteo.com/v1/search", {"name": "北京", "count": 1}),
        ("https://geocoding-api.open-meteo.com/v1/nope", None),
        ("https://api.open-meteo.com/v1/forecast", {"latitude": 999, "longitude": 0, "current": "temperature_2m"}),
        ("https://api.open-meteo.com/v1/forecast", {"latitude": 39.9}),
        ("https://httpbin.org/status/500", None),
    ]

    for url,parms in test_url:
        probe(url,parms)


if __name__ == '__main__':
    main()