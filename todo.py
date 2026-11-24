#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行待办清单（第 1 周交付物）：增删改查 + JSON 持久化。

数据结构（todos.json）::

    [
        {"id": 1, "text": "买牛奶", "done": false, "created_at": "2026-11-04T17:30"}
    ]

用法::

    python todo.py                  # 交互菜单
    python todo.py --selftest       # 离线自检（用临时文件，不动真实数据）
    python todo.py --file D:/x.json # 指定数据文件

设计要点：
    1. 数据文件路径用 Path(__file__) 定位，在哪个目录运行都不会找错。
    2. 保存用"临时文件 + os.replace"原子替换，写到一半崩了也不会毁掉原文件。
    3. 读文件的所有失败（不存在 / 空 / 损坏 / 类型不对）都降级成空列表并提示。
    4. 业务函数只改内存并返回结果，写盘由调用方显式决定（便于测试、便于加审批）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

Todo = dict[str, Any]

DATA_FILE = Path(__file__).resolve().parent / "todos.json"

MENU = """
---------------- 待办清单 ----------------
  1) 添加      2) 查看      3) 完成
  4) 删除      5) 清空已完成       q) 退出
------------------------------------------"""


# ============================================================================
# 一、持久化层：只负责把 list[dict] 从磁盘读出来 / 写回去
# ============================================================================


def load_todos(path: Path = DATA_FILE) -> list[Todo]:
    """读取待办列表。

    以下情况一律返回空列表，不抛异常（避免一个坏文件让整个程序打不开）：
    文件不存在、空文件、内容不是合法 JSON、顶层不是列表。
    非法的单条记录（缺 id / text）会被过滤掉。
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as exc:
        print(f"[警告] {path.name} 不是合法 JSON（{exc}），本次按空列表处理。", file=sys.stderr)
        return []
    except OSError as exc:                      # 权限、被占用、磁盘错误
        print(f"[错误] 读取 {path.name} 失败：{exc}", file=sys.stderr)
        return []

    if not isinstance(data, list):
        print(f"[警告] {path.name} 顶层应为列表，实际是 {type(data).__name__}。", file=sys.stderr)
        return []

    return [t for t in data if isinstance(t, dict) and "id" in t and "text" in t]


def save_todos(todos: list[Todo], path: Path = DATA_FILE) -> bool:
    """原子保存到 JSON，成功返回 True，失败打印原因并返回 False。

    为什么不用 open(path, "w") 直接覆盖：覆盖那一刻文件已被清空，
    如果随后写失败/断电，原数据就永久没了。先写同目录临时文件、fsync 落盘，
    再用 os.replace 原子替换——旧文件在替换前始终完好。
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix=".todos-", suffix=".tmp", dir=str(path.parent))
    except OSError as exc:
        print(f"[错误] 无法创建临时文件：{exc}", file=sys.stderr)
        return False

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(todos, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except (OSError, TypeError) as exc:
        Path(tmp_path).unlink(missing_ok=True)
        print(f"[错误] 保存失败：{exc}", file=sys.stderr)
        return False

    return True


# ============================================================================
# 二、业务层：纯内存操作，输入输出明确，方便单元测试
# ============================================================================


def next_id(todos: list[Todo]) -> int:
    """返回下一个可用 id；删掉中间的元素后也不复用旧 id。"""
    return max((t.get("id", 0) for t in todos), default=0) + 1


def add_todo(todos: list[Todo], text: str) -> Todo:
    """在列表里追加一条待办并返回它（不写盘）。"""
    todo: Todo = {
        "id": next_id(todos),
        "text": text.strip(),
        "done": False,
        "created_at": datetime.now().isoformat(timespec="minutes"),
    }
    todos.append(todo)
    return todo


def find_todo(todos: list[Todo], todo_id: int) -> Todo | None:
    """按 id 查找一条待办，找不到返回 None。"""
    for todo in todos:
        if todo.get("id") == todo_id:
            return todo
    return None


def mark_done(todos: list[Todo], todo_id: int) -> bool:
    """把指定 id 标记为完成；找不到返回 False。改完要调用方自己 save。"""
    todo = find_todo(todos, todo_id)
    if todo is None:
        return False
    todo["done"] = True
    return True


def remove_todo(todos: list[Todo], todo_id: int) -> bool:
    """删除指定 id；找不到返回 False。

    用列表推导式重建，而不是 for 循环里 del：边遍历边删会漏掉相邻元素，
    而且 del 一个循环变量根本不会改动列表本身。
    ``todos[:] = ...`` 是原地替换，调用方持有的列表对象依然有效。
    """
    remain = [t for t in todos if t.get("id") != todo_id]
    if len(remain) == len(todos):
        return False
    todos[:] = remain
    return True


def format_todo(todo: Todo) -> str:
    """把一条待办渲染成一行文本。"""
    mark = "x" if todo.get("done") else " "
    return f"[{mark}] {todo.get('id'):>3}  {todo.get('text', '')}  ({todo.get('created_at', '-')})"


def print_all(todos: list[Todo]) -> None:
    """打印全部待办，并在末尾给出统计。"""
    if not todos:
        print("还没有待办，输入 1 添加一条。")
        return
    for todo in todos:
        print(format_todo(todo))
    done = sum(1 for t in todos if t.get("done"))
    print(f"共 {len(todos)} 条，已完成 {done} 条，未完成 {len(todos) - done} 条。")


# ============================================================================
# 三、交互层：只做"读输入 → 调业务层 → 决定是否写盘 → 打印结果"
# ============================================================================


def read_line(prompt: str) -> str | None:
    """读一行输入；EOF 或 Ctrl+C 返回 None，由调用方决定如何退出。"""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return None


def parse_id(raw: str) -> int | None:
    """把用户输入解析成编号；非法输入打印提示并返回 None。"""
    raw = raw.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        print(f"“{raw}” 不是数字编号。")
        return None


def interactive(path: Path = DATA_FILE) -> int:
    """菜单主循环，返回进程退出码（0 正常）。"""
    todos = load_todos(path)
    print(f"数据文件：{path}")

    while True:
        print(MENU)
        raw = read_line("请选择 > ")
        if raw is None:
            print("\n再见。")
            return 0
        choice = raw.strip().lower()

        if choice in {"q", "quit", "exit", "退出"}:
            print("再见。")
            return 0

        if choice == "1":
            text = read_line("要做什么：")
            if text is None:
                print("\n再见。")
                return 0
            if not text.strip():
                print("内容不能为空。")
                continue
            todo = add_todo(todos, text)
            if save_todos(todos, path):
                print(f"已添加 #{todo['id']}：{todo['text']}")

        elif choice == "2":
            print_all(todos)

        elif choice == "3":
            raw_id = read_line("要完成哪条（编号）：")
            if raw_id is None:
                print("\n再见。")
                return 0
            todo_id = parse_id(raw_id)
            if todo_id is None:
                continue
            if not mark_done(todos, todo_id):
                print(f"没有编号为 {todo_id} 的待办。")
            elif save_todos(todos, path):
                print(f"已完成 #{todo_id}")

        elif choice == "4":
            raw_id = read_line("要删除哪条（编号）：")
            if raw_id is None:
                print("\n再见。")
                return 0
            todo_id = parse_id(raw_id)
            if todo_id is None:
                continue
            if not remove_todo(todos, todo_id):
                print(f"没有编号为 {todo_id} 的待办。")
            elif save_todos(todos, path):
                print(f"已删除 #{todo_id}")

        elif choice == "5":
            before = len(todos)
            todos[:] = [t for t in todos if not t.get("done")]
            if save_todos(todos, path):
                print(f"已清理 {before - len(todos)} 条已完成的待办。")

        else:
            print("没有这个选项，请重新选择。")


# ============================================================================
# 四、离线自检：把上面每一层的边界情况都跑一遍（不碰真实 todos.json）
# ============================================================================


def selftest() -> int:
    """验证增删改查、持久化、损坏降级、中文往返。

    数据写在本项目目录下的一个临时文件里（不新建子目录，兼容各种受限环境），
    测完无论成败都删掉，不会碰你真实的 todos.json。
    """
    path = DATA_FILE.parent / f".todos-selftest-{os.getpid()}.json"
    try:
        todos: list[Todo] = []

        # 1) 文件不存在 → 空列表
        assert load_todos(path) == [], "文件不存在时应返回空列表"

        # 2) 连续添加，id 递增
        first = add_todo(todos, "买牛奶")
        second = add_todo(todos, "写周报")
        assert (first["id"], second["id"]) == (1, 2), "id 应从 1 开始递增"
        assert save_todos(todos, path), "保存应成功"

        # 3) 重新读盘 —— 模拟"关掉程序重开"
        reloaded = load_todos(path)
        assert [t["text"] for t in reloaded] == ["买牛奶", "写周报"], "重开后数据应还在"

        # 4) 完成 / 找不到
        assert mark_done(reloaded, 1) and reloaded[0]["done"], "标记完成应生效"
        assert not mark_done(reloaded, 999), "不存在的 id 应返回 False"
        assert save_todos(reloaded, path)

        # 5) 删除中间一条后，剩下的 id 不受影响；新加的 id 不复用
        assert remove_todo(reloaded, 1), "删除应成功"
        assert not remove_todo(reloaded, 1), "重复删除应返回 False"
        assert [t["id"] for t in reloaded] == [2], "删除后其它 id 不应变化"
        assert add_todo(reloaded, "新任务")["id"] == 3, "已删除的 id 不应被复用"

        # 6) 坏文件：非法 JSON / 顶层不是列表 / 空文件 → 都降级为空列表
        path.write_text("{不是合法json", encoding="utf-8")
        assert load_todos(path) == [], "非法 JSON 应降级为空列表"
        path.write_text('{"a": 1}', encoding="utf-8")
        assert load_todos(path) == [], "顶层不是列表应降级为空列表"
        path.write_text("", encoding="utf-8")
        assert load_todos(path) == [], "空文件应降级为空列表"

        # 7) 中文往返不乱码（ensure_ascii=False）
        path.write_text(
            json.dumps([{"id": 7, "text": "中文不乱码", "done": False, "created_at": "x"}],
                       ensure_ascii=False),
            encoding="utf-8",
        )
        assert load_todos(path)[0]["text"] == "中文不乱码", "中文读写不应乱码"
    finally:
        path.unlink(missing_ok=True)

    print("✅ 自检通过：增 / 删 / 改 / 查、持久化、损坏降级、中文往返 全部正常。")
    return 0


# ============================================================================
# 五、入口
# ============================================================================


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="命令行待办清单")
    parser.add_argument("--selftest", action="store_true", help="离线自检，不碰真实数据")
    parser.add_argument(
        "--file", type=Path, default=DATA_FILE,
        help=f"指定数据文件（默认 {DATA_FILE.name}）",
    )
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    return interactive(args.file)


if __name__ == "__main__":
    sys.exit(main())
