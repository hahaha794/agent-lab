#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

TODO = dict[str, Any]

DATA_FILE = Path(__file__).resolve().parent / 'todos.json'

MENU = """
                待办清单
1)添加    2）查看    3）删除    4）完成    q)退出
"""

def load(path:Path = DATA_FILE)->list[TODO]:
    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    except json.decoder.JSONDecodeError:
        print(f'不是合法JSON，本次按空列表处理')
        return []

    return [t for t in data if isinstance(t,dict) and "text" in t and "id" in t]

def save(todos: list[TODO], path: Path = DATA_FILE)->bool:
    try:
        with path.open('w', encoding='utf-8') as f:
            json.dump(todos, f, ensure_ascii=False, indent=4)
    except OSError as e:
        print(f'保存失败{e}', file=sys.stderr)
        return False
    return True

def next_id(todos:list[TODO])->int:
    max_id = 0
    for t in todos:
        temp_id = t.get("id")
        if temp_id > max_id:
            max_id = temp_id

    return max_id+1

def add(todos:list[TODO],text: str)->list[TODO]:
    todo: TODO = {
        "id" : next_id(todos),
        "text" : text.strip(),
        "done" : False,
        "date" : datetime.now().isoformat(),
    }
    todos.append(todo)
    return todos

def find(todos:list[TODO],id: int)->TODO | None:
    for t in todos:
        if t["id"] == id:
            return t
    return None

def remove_todo(todos:list[TODO],id: int)->bool:
    remain = [t for t in todos if t["id"] != id]
    if len(remain) == len(todos):
        return False
    todos[:] = remain
    return True

def mark_done(todos:list[TODO],id: int)->bool:
    for t in todos:
        if t["id"] == id:
            t["done"] = True
            return True
    return False

def ask_id(prompt: str) -> int | None:
    raw = input(prompt).strip()
    try:
        return int(raw)
    except ValueError:
        print('请输入数字编号')
        return None

def main()->int | None:
    todos = load()
    while True:
        print(MENU)
        raw = input("请输入->\n")

        choice = raw.strip().lower()
        if choice in {'q', 'quit', 'exit','退出'}:
            print('再见')
            return 0

        if choice == '1':
            text = input("请输入任务->\n")
            if not text.strip():
                print('输入不能为空')
                continue

            todos = add(todos, text)
            if save(todos):
                print('保存成功')

        elif choice == '2':
            if not todos:
                print('还没有待办')
            else:
                for t in todos:
                    mark = 'x' if t.get('done') else ' '
                    print(f"[{mark}] {t['id']:>3}  {t['text']}")

        elif choice == '3':
            todo_id = ask_id('请输入要删除的序号->\n')

            if todo_id is None:
                print('序号不能为空')
                continue

            if remove_todo(todos, todo_id):
                print(f'已删除{todo_id}')
                save(todos)
            else:
                print(f'没有编号为{todo_id}的待办')

        elif choice == '4':
            todo_id = ask_id('请输入要完成的序号->\n')

            if todo_id is None:
                print('序号不能为空')
                continue

            if mark_done(todos, todo_id):
                print(f'已完成{todo_id}')
                save(todos)
            else:
                print(f'没有编号为 {todo_id} 的待办')

        else:
            print('没有这个选项')

if __name__ == '__main__':
    sys.exit(main())