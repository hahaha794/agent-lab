#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict

DEFAULT_EXCLUDES = {".venv", "__pycache__", ".git"}

def read_text_safe(path: Path) -> str | None:
    """用 UTF-8 读文本；任何失败（不存在 / 是目录 / 编码不对 / 没权限）→ 返回 None，不抛异常。"""
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError,OSError):
        return None

def count_lines(path: Path) -> int:
    """返回行数。

    - 空文件 → 0
    - 末尾没有换行符的最后一行也算一行
    - 必须逐行迭代（不许把整个文件读进内存）
    """
    n = 0
    with open(path,"r", encoding="utf-8") as f:
        for _ in f:
            n += 1
    return n

def longest_line(path: Path) -> str:
    """返回最长的一行（不含行尾的 \\r\\n）。

    - 并列时取第一条
    - 空文件 → ""
    """
    longest_line_1 = ""
    with open(path,"r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if len(line) > len(longest_line_1):
                longest_line_1 = line
    return longest_line_1

def write_atomic(path: Path, text: str) -> None:
    """原子写入 UTF-8 文本。

    - 先写同目录的临时文件，再 os.replace 覆盖目标
    - 父目录不存在时自动创建
    - 结束后不能留下临时文件
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)

class ScanResult(TypedDict):
    files: int
    lines: int
    longest_len: int
    longest_file: str
    skipped: list[str]


def scan_dir(root: Path, excludes: set[str] | None = None) -> ScanResult:
    """统计目录下的文本文件。返回：

    {
      "files": int,          # 成功读出来的文件数
      "lines": int,          # 这些文件的行数之和
      "longest_len": int,    # 最长行的字符数
      "longest_file": str,   # 最长行所在的文件（相对 root、用 / 分隔）
      "skipped": list[str],  # 读不了的文件（相对 root、排序）
    }

    - excludes=None → 用默认 {".venv", "__pycache__", ".git"}
    - root 不存在 → 返回全 0 的 dict，不抛异常
    """
    info:ScanResult = {
        "files": 0,
        "lines": 0,
        "longest_len": 0,
        "longest_file": "",
        "skipped": [],
    }

    if not root.is_dir():
        return info

    ex = DEFAULT_EXCLUDES if excludes is None else excludes
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in ex for part in rel.parts):
            continue
        text = read_text_safe(p)
        if text is None:
            info["skipped"].append(rel.as_posix())
            continue
        lines = text.splitlines()
        info["files"] += 1
        info["lines"] += len(lines)

        best = max((len(line) for line in lines), default=0)
        if best > info["longest_len"]:
            info["longest_len"] = best
            info["longest_file"] = rel.as_posix()

    info["skipped"].sort()
    return info

if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent
    a = scan_dir(ROOT, excludes=DEFAULT_EXCLUDES)
    skipped = a["skipped"]
    skipped_names = "、".join(p for p in skipped) or "无"

    print(
        f"==notes目录读后感==\n"
        f"可读文件：{a['files']}\n"
        f"总行数：{a['lines']}\n"
        f"最长行：{a['longest_len']}字符（在{a['longest_file']}）\n"
        f"跳过：{len(skipped)}个（{skipped_names}）"
    )