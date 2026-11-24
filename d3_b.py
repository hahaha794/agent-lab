#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import requests


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

def fetch_json(url: str, params: dict | None = None, timeout: float = 10) -> dict:
    """成功返回 dict；失败抛 WeatherError 的子类。"""
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError as e:
        raise UpstreamError(e.response.status_code, e.response.text) from e
    except requests.Timeout as e:
        raise NetworkError('请求超时') from e
    except requests.ConnectionError as e:
        raise NetworkError('连不上网络') from e
    except requests.JSONDecodeError as e:
        raise UpstreamError(0,'返回内容不是合法Json') from e
    return data

def lookup_city(urls: list[tuple[str,any]]) -> None:
    for url, params in urls:
        try:
            data = fetch_json(url, params=params, timeout=2)
            if data.get("results"):
                print("OK")
            else:
                raise CityNotFound()
        except WeatherError as e:
            print(type(e).__name__, ":", e)

def main():
    CASES = [
        ("https://geocoding-api.open-meteo.com/v1/search",
         {"name": "北京", "count": 1}),  # 正常
        ("https://geocoding-api.open-meteo.com/v1/nope",
         None),  # 404
        ("http://127.0.0.1:9",
         None),  # 死端口
    ]
    lookup_city(CASES)


if __name__ == "__main__":
    main()