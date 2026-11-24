#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import logging
from datetime import datetime
import json
import traceback

def boom(kind: str) -> None:
    """按 kind 制造对应异常。"""
    match kind:
        case "KeyError":
            _ = {}["missing_key"]
        case "IndexError":
            _ = [][0]
        case "AttributeError":
            obj = None
            _ = obj.some_attr
        case "TypeError":
            # json 不认识 datetime 对象
            _ = json.dumps({"time": datetime.now()})
        case "ValueError":
            _ = int("abc")
        case "ZeroDivisionError":
            _ = 1 / 0
        case _:
            raise ValueError(f"未知的 kind: {kind}")


def test_case() -> None:
    """输出各种错误类型"""
    error = ["KeyError","IndexError","AttributeError",
             "TypeError","ValueError","ZeroDivisionError"]

    for kind in error:
        try:
            boom(kind)
        except Exception as e:
            print("=" * 60)
            print(f"[{kind}]")
            print(f"  print(e)          -> {e}")  # 只有一行
            print(f"  format_exc()  ->\n{traceback.format_exc()}")
            logging.exception("同一错误，换成日志")  # 输出到 stderr


if __name__ == "__main__":
    test_case()