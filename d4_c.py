#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict

import requests

RETRYABLE_STATUS = {429, 500, 502, 503, 504}

class WeatherError(Exception):
    """本模块所有错误的基类。"""

class NetworkError(WeatherError):
    """连不上网络。"""

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

def fetch_one(url:str, params:Dict | None = None, timeout=(3.05, 10)) -> dict:
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
        timeout=(3.05, 10),
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
            print(f"第{attempt}次尝试失败（{type(e).__name__}），将在{delay:.1f}秒后重试")
            time.sleep(delay)

    raise RuntimeError("重试次数已用尽")

# ============================================================ 六、本地假服务器
class ScriptedHandler(BaseHTTPRequestHandler):
    """按 statuses 列表依次返回状态码，最后一个会一直重复。"""

    statuses: list[int] = [200]
    retry_after: str | None = None
    calls = 0

    def do_GET(self) -> None:
        if self.path.startswith("/html"):
            body = b"<html><body>not json</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        ScriptedHandler.calls += 1
        index = min(ScriptedHandler.calls - 1, len(ScriptedHandler.statuses) - 1)
        code = ScriptedHandler.statuses[index]
        body = json.dumps({"ok": code == 200, "calls": ScriptedHandler.calls}).encode("utf-8")

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if ScriptedHandler.retry_after:
            self.send_header("Retry-After", ScriptedHandler.retry_after)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        pass                            # 关掉自带访问日志


def start_server(statuses: list[int], retry_after: str | None = None):
    """起一个假服务器，返回 (server, base_url)。端口随机。"""
    ScriptedHandler.statuses = statuses
    ScriptedHandler.retry_after = retry_after
    ScriptedHandler.calls = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), ScriptedHandler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/"

# ============================================================ 七、验收测试
def run_tests() -> int:
    passed = total = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal passed, total
        total += 1
        passed += int(ok)
        print(f"  {'✅' if ok else '❌'} {name}{detail}")

    # 1) 正常：1 次请求
    server, url = start_server([200])
    try:
        data = fetch_json(url, attempts=3, base_delay=0.05, timeout=(1, 2))
        check("正常 → 返回 dict", data.get("ok") is True)
        check("正常 → 只请求 1 次", ScriptedHandler.calls == 1, f"（实际 {ScriptedHandler.calls}）")
    finally:
        server.shutdown()
        server.server_close()

    # 2) 前 2 次 503，第 3 次 200
    server, url = start_server([503, 503, 200])
    try:
        data = fetch_json(url, attempts=3, base_delay=0.05, timeout=(1, 2))
        check("503×2 后成功", data.get("ok") is True)
        check("503×2 后成功 → 共 3 次请求", ScriptedHandler.calls == 3, f"（实际 {ScriptedHandler.calls}）")
    finally:
        server.shutdown()
        server.server_close()

    # 3) 一直 503
    server, url = start_server([503])
    try:
        try:
            fetch_json(url, attempts=3, base_delay=0.02, timeout=(1, 2))
            check("一直 503 → 应抛 RetryableError", False)
        except RetryableError as e:
            check("一直 503 → 抛 RetryableError", True, f"（status={e.status}）")
            check("一直 503 → 共试 3 次", ScriptedHandler.calls == 3, f"（实际 {ScriptedHandler.calls}）")
    finally:
        server.shutdown()
        server.server_close()

    # 4) 404：不重试
    server, url = start_server([404])
    try:
        try:
            fetch_json(url, attempts=3, base_delay=0.02, timeout=(1, 2))
            check("404 → 应抛 UpstreamError", False)
        except UpstreamError as e:
            check("404 → 抛 UpstreamError", True, f"（status={e.status}）")
            check("404 → 不重试（只 1 次请求）", ScriptedHandler.calls == 1, f"（实际 {ScriptedHandler.calls}）")
    finally:
        server.shutdown()
        server.server_close()

    # 5) 429 + Retry-After
    server, url = start_server([429, 200], retry_after="0.05")
    try:
        data = fetch_json(url, attempts=2, base_delay=1.0, timeout=(1, 2))
        check("429 带 Retry-After → 重试后成功", data.get("ok") is True)
        check("429 → 共 2 次请求", ScriptedHandler.calls == 2, f"（实际 {ScriptedHandler.calls}）")
    finally:
        server.shutdown()
        server.server_close()

    # 6) 返回 HTML：不是 JSON
    server, url = start_server([200])
    try:
        try:
            fetch_json(url + "html", attempts=3, base_delay=0.02, timeout=(1, 2))
            check("HTML → 应抛 UpstreamError", False)
        except UpstreamError as e:
            check("HTML → 抛 UpstreamError(0)", e.status == 0)
    finally:
        server.shutdown()
        server.server_close()

    # 7) 死端口：网络错误 + 重试
    try:
        fetch_json("http://127.0.0.1:1/", attempts=3, base_delay=0.02, timeout=(0.5, 0.5))
        check("死端口 → 应抛 NetworkError", False)
    except NetworkError:
        check("死端口 → 抛 NetworkError", True)

    print(f"\n{passed}/{total} 通过")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(run_tests())