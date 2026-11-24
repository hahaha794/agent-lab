#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import random
import time
from typing import Dict
from dotenv import load_dotenv
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

GEO_URL = os.getenv("GEO_URL", "https://geocoding-api.open-meteo.com/v1/search")

RETRYABLE_STATUS = {429, 500, 502, 503, 504}

class WeatherError(Exception):
    """本模块所有错误的基类。"""

class NetworkError(WeatherError):
    """连不上网络。"""

class CityNotFoundError(WeatherError):
    """找不到城市"""

class RetryableError(WeatherError):
    """临时故障，可以重试。"""
    def __init__(self, status: int, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after

class UpstreamError(WeatherError):
    """服务器返回了错误状态。"""
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status

def _parse_retry_after(response: requests.Response) -> float | None:
    """从响应头中解析Retry-After，如果没有或者格式不认识就返回None"""
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None

def fetch_one(url:str, params:Dict | None = None, timeout=10.0) -> dict:
    """成功返回 dict；失败时根据错误类型执行重试或直接报错"""
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError as e:
        code = e.response.status_code
        if code in RETRYABLE_STATUS:
            raise RetryableError(code, f"服务暂时不可用（HTTP {code}）",
                                 retry_after=_parse_retry_after(e.response)) from e
        raise UpstreamError(code, f"请求失败（HTTP {code}）") from e
    except requests.Timeout as e:
        raise NetworkError('请求超时') from e
    except requests.ConnectionError as e:
        raise NetworkError('连不上网络') from e
    except requests.JSONDecodeError as e:
        raise UpstreamError(0,'返回内容不是合法Json') from e
    return data

def fetch_json(
        url:str,
        params:Dict | None = None,
        timeout=10.0,
        attempts: int=3,
        base_delay: float = 1.0,
) -> dict:
    """最多只尝试attempts次：只重试临时故障，其余直接抛出"""
    if attempts < 1:
        raise ValueError("重试次数不能小于1！")
    for attempt in range(1, attempts + 1):
        try:
            return fetch_one(url, params, timeout)
        except (RetryableError,NetworkError) as e:
            if attempt == attempts:
                raise
            retry_after = getattr(e, 'retry_after', None)
            base = retry_after if retry_after is not None else base_delay * 2 ** (attempt - 1)
            delay = base + random.uniform(0, 0.3)
            print(f"    第 {attempt} 次失败（{type(e).__name__}），{delay:.2f} 秒后重试")
            time.sleep(delay)

    raise RuntimeError("重试次数已用尽")

def geocode(city: str, geocode_url: str = GEO_URL, timeout=10.0) -> tuple[float, float]:
    response_json = fetch_json(geocode_url,
                            params={"name": city, "count": 1, "language": "zh"},
                            timeout=timeout)
    if response_json.get("results"):
        lat = response_json["results"][0]["latitude"]
        lon = response_json["results"][0]["longitude"]
        return lat, lon
    else:
        raise CityNotFoundError(f"找不到城市{city}，请检查写法（支持中文/英文/拼音）")

def get_weather(city:str,
                unit:str = "celsius",
                geocode_url=GEO_URL,
                timeout=10.0,
                attempts: int = 3,
                base_delay: float = 1.0,)->dict:
    try:
        geo_lat, geo_lon = geocode(city, geocode_url=geocode_url, timeout=timeout)
    except CityNotFoundError:
        raise CityNotFoundError

    temp_unit = "celsius" if unit == "celsius" else "fahrenheit"
    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_resp = fetch_json(
        weather_url,
        params={
            "latitude": geo_lat,
            "longitude": geo_lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
            "temperature_unit": temp_unit,
        },
        timeout=timeout,
        attempts=attempts,
        base_delay=base_delay,
    )
    data = weather_resp.get("current")  # ✅ 是 dict

    # 3. 天气代码转可读描述（WMO 标准，Open-Meteo 官方映射的简化版）
    wmo_map = {
        0: "晴", 1: "大部晴朗", 2: "部分多云", 3: "阴",
        45: "雾", 48: "沉积雾",
        51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
        61: "小雨", 63: "中雨", 65: "大雨",
        71: "小雪", 73: "中雪", 75: "大雪",
        80: "小阵雨", 81: "阵雨", 82: "强阵雨",
        95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹",
    }

    return {
        "city": city,
        "temperature": data["temperature_2m"],
        "feels_like": data["apparent_temperature"],
        "unit": "°C" if unit == "celsius" else "°F",
        "humidity": data["relative_humidity_2m"],
        "wind_speed": data["wind_speed_10m"],
        "description": wmo_map.get(data["weather_code"], f"未知天气代码: {data['weather_code']}"),
    }