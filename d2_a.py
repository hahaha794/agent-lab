#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import requests


def show(usl,parms= None,timeout: float = 10):
    r = requests.get(usl,params=parms,timeout= timeout)
    print(f"{r.status_code} {r.reason:<20} ok={r.ok!s:<5} | {r.text[:60]}")

def main():
    test_url = [
        ("https://geocoding-api.open-meteo.com/v1/search", {"name": "北京", "count": 1}),
        ("https://geocoding-api.open-meteo.com/v1/nope", None),
        ("https://api.open-meteo.com/v1/forecast", {"latitude": 999, "longitude": 0, "current": "temperature_2m"}),
        ("https://api.open-meteo.com/v1/forecast", {"latitude": 39.9}),
        ("https://httpbin.org/status/500", None),
    ]

    for url,parms in test_url:
        show(url,parms)


if __name__ == '__main__':
    main()