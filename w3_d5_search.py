#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from pathlib import Path

DEFAULT_EXCLUDES = {".venv", "__pycache__", ".git"}

def search_file(path: Path, keyword: str, ignore_case: bool = False) -> list[tuple[int, str]]:
    """在单个文件里找关键词。

    - 返回 [(行号, 行内容)]，行号从 1 开始
    - 行内容不含行尾的 \\r\\n
    - keyword 按【字面量】匹配（a.b 不匹配 axb）
    - 文件不存在 / 不是文件 / 读不了（编码或权限）→ []
    """
    if not path.is_file():
        return []
    if not keyword:
        return []

    flags = re.IGNORECASE if ignore_case else 0
    try:
        pat = re.compile(re.escape(keyword), flags)
    except re.error:
        return []  # 理论上 escape 后不会错，防御性

    out: list[tuple[int, str]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                content = line.rstrip("\r\n")
                if pat.search(content):
                    out.append((lineno, content))
    except (OSError, UnicodeError):
        return []  # 权限 / 编码 / 其他 I/O 错误
    return out

def search_dir(
    root: Path,
    keyword: str,
    ignore_case: bool = False,
    exts: set[str] | None = None,
    excludes: set[str] | None = None,
) -> list[tuple[str, int, str]]:
    """递归搜索目录。

    - 返回 [(相对路径, 行号, 行内容)]，路径用 / 分隔（posix 风格）
    - 结果按 (路径, 行号) 升序排序
    - excludes=None → 用默认 {".venv", "__pycache__", ".git"}
    - exts=None → 不按后缀过滤；否则只搜这些后缀（大小写不敏感）
    - root 不存在 → []
    - 读不了的文件跳过（不抛异常）
    """
    out: list[tuple[str, int, str]] = []

    if not root.is_dir():
        return []
    if not keyword:
        return []

    ex = DEFAULT_EXCLUDES if excludes is None else excludes
    ext_set = {e.lower() for e in exts} if exts else None
    for g in root.rglob("*"):
        if not g.is_file():
            continue
        rel = g.relative_to(root)
        if any(part in ex for part in rel.parts):
            continue

        if exts is None or rel.suffix.lower() in ext_set:
            for lineno, line in search_file(g, keyword, ignore_case=ignore_case):
                temp_out = (rel.as_posix(), lineno, line)
                out.append(temp_out)

    return  sorted(out, key=lambda h: (h[0], h[1]))

def format_hit(path: str, lineno: int, line: str, context: int = 0) -> str:
    """格式化成 "路径:行号: 内容"。

    - context > 0 且内容长度 > context 时，截断到 context 个字符并加 "…"
    - context = 0（默认）→ 不截断
    """
    text = line
    if 0 < context < len(text):
        text = text[:context] + "…"
    return f"{path}:{lineno}: {text}"


def summarize_hits(hits: list[tuple[str, int, str]]) -> dict:
    """统计命中。

    返回 {"files": int, "matches": int, "by_file": {路径: 命中数}}
    - files 是【去重后】的文件数
    - 空列表 → {"files": 0, "matches": 0, "by_file": {}}
    """
    out = {
        "files": 0,
        "matches": 0,
        "by_file": {},
    }

    for hit in hits:
        out["by_file"][hit[0]] = out["by_file"].get(hit[0], 0) + 1

    out["files"] = len(out["by_file"])
    out["matches"] = len(hits)
    return out
