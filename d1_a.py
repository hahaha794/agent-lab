#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import requests

resp = requests.get(url = 'https://geocoding-api.open-meteo.com/v1/search',
             params = {'name':'北京', 'count':1, 'language':'zh'},timeout=10)

print(resp.status_code)
print(resp.url)
print(resp.headers.get('content-type'))
print(resp.text[:200])
data = resp.json()
print(data)
print(len(data['results']))