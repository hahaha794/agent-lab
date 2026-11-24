#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D3 练习 1：探测 requests 的异常树，看清"哪些异常带 response"。"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

import requests

NOT_FOUND_URL = "https://geocoding-api.open-meteo.com/v1/nope"


# --------------------------------------------------------------------------
# 场景 3 专用：一个"连得上、但 2 秒后才响应"的本地服务器
# --------------------------------------------------------------------------
class SlowHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        time.sleep(2)  # 故意拖时间，让客户端读超时
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"slow")
        except (BrokenPipeError, ConnectionAbortedError):
            pass  # 客户端已经超时断开，这里报错不算问题

    def log_message(self, *args) -> None:
        pass  # 关掉它自带的访问日志，别污染输出


def start_slow_server() -> tuple[ThreadingHTTPServer, int]:
    """在随机空闲端口起一个慢服务器，返回 (server, port)。"""
    server = ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


# --------------------------------------------------------------------------
# 统一跑一个场景，并打印"类型 / 继承链 / 有没有 response / 消息"
# --------------------------------------------------------------------------
def show(title: str, action: Callable[[], object]) -> None:
    print(f"\n=== {title} ===")
    try:
        action()
    except requests.RequestException as e:
        print(f"  类型        : {type(e).__name__}")
        print(f"  继承链      : {' -> '.join(c.__name__ for c in type(e).__mro__[:4])}")
        print(f"  .response   : {'有（Response 对象）' if e.response is not None else 'None'}")
        print(f"  也是 json.JSONDecodeError: {isinstance(e, json.JSONDecodeError)}")
        print(f"  消息(前70)  : {str(e)[:70]}")
    except json.JSONDecodeError as e:
        print(f"  类型        : {type(e).__name__}（来自 json 模块）")
        print(f"  消息(前70)  : {str(e)[:70]}")
    else:
        print("  没有抛异常（这次请求成功了）")


def main() -> None:
    server, slow_port = start_slow_server()
    try:
        # 1) 404：服务器回应了，但状态码不对
        def case_404() -> None:
            requests.get(NOT_FOUND_URL, timeout=10).raise_for_status()

        # 2) 连不上：DNS 解析失败（.invalid 是 RFC 保留域名，永远解析不到）
        def case_connection_error() -> None:
            requests.get("http://nothing.invalid/", timeout=3)

        # 3) 连得上，但读不到响应
        def case_read_timeout() -> None:
            requests.get(f"http://127.0.0.1:{slow_port}/", timeout=0.5)

        # 4) 拿到响应了，但内容不是 JSON
        def case_bad_json() -> None:
            requests.get("https://example.com", timeout=10).json()

        show("1) 404        -> HTTPError", case_404)
        show("2) DNS 失败   -> ConnectionError", case_connection_error)
        show("3) 连上不返回 -> ReadTimeout", case_read_timeout)
        show("4) 内容是 HTML -> JSONDecodeError", case_bad_json)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()