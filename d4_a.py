#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

import requests

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
        print(f"  消息        : {str(e)}")
    else:
        print("  没有抛异常（这次请求成功了）")


def main() -> None:
    server, slow_port = start_slow_server()
    try:
        timeout_url = f"http://127.0.0.1:{slow_port}/"
        def timeout_1()-> None:
            requests.get(timeout_url, timeout=0.1).raise_for_status()
        def timeout_2()-> None:
            requests.get(timeout_url, timeout=1.0).raise_for_status()
        def timeout_3()-> None:
            requests.get(timeout_url, timeout=5.0).raise_for_status()

        start1 = time.time()
        show("当timeout为0.1时", timeout_1)
        end1 = time.time()
        print(f"  当timeout为0.1时前后耗时为: {end1 - start1} ")
        start2 = time.time()
        show("当timeout为1.0时", timeout_2)
        end2 = time.time()
        print(f"  当timeout为1.0时前后耗时为: {end2 - start2} ")
        start3 = time.time()
        show("当timeout为5.0时", timeout_3)
        end3 = time.time()
        print(f"  当timeout为5.0时前后耗时为: {end3 - start3} ")

    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()