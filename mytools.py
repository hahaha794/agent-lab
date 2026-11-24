#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

"""mytools —— 学习过程中沉淀的小工具集。

包含四类能力：
    - 读文件（容错，读不了返回 None）
    - 在目录里搜索关键词（返回结构化结果）
    - 从文本里提取 URL / 邮箱
    - 原子写文件（不会写坏原文件）

所有函数都不打印内容，只返回数据；打印是调用方的事。

用法：
    python mytools.py --selftest
    >>> from mytools import search_text
    >>> search_text("Python", "notes")
"""


import os
import re
import sys
import shutil
import tempfile
from pathlib import Path
from typing import TypedDict

DEFAULT_EXCLUDES = {".venv", "__pycache__", ".git"}

def search_file(path: Path, keyword: str, ignore_case: bool = False) -> list[tuple[int, str]]:
    """在单个文件里找关键词。

    - 返回 [(行号, 行内容)]，行号从 1 开始
    - 行内容不含行尾的 \\r\\n
    - keyword 按【字面量】匹配（a.b 不匹配 axb）
    - 文件不存在 / 不是文件 / 读不了（编码或权限）→ []

    Args:
        path (Path): 要搜索的路径
        keyword (str): 要搜索的关键词
        ignore_case (bool): 大小写敏感

    Returns:
        命中列表，每项为["行号"，"行内容“]

    Raises:
        OSError, UnicodeError:# 权限 / 编码 / 其他 I/O 错误
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

class SearchResult(TypedDict):
    path: str
    lines: int
    text: str

def search_text(keyword:str, root:Path|str=".",
                *, ignore_case:bool = False, exts:set[str] | None=None,
                excludes: set[str] | None = None,context:int=0)->list[SearchResult]:
    """在目录里搜索关键词，返回命中的行。

        Args:
            keyword: 要搜的词，按字面量匹配（不是正则）。
            root: 搜索起点，可以是 Path 或字符串。
            ignore_case: True 时大小写不敏感。
            exts: 只搜这些后缀（如 {".md"}）；None 表示不过滤。
            excludes: 要跳过的目录或文件列表
            context: 命中行超过这么长就截断，0 表示不截断。

        Returns:
            命中列表，每项是 {"path": str, "lines": int, "text": str}，
            按 (path, line) 升序。

        Raises:
            不抛异常：读不了的文件会被跳过。
        """
    out:list[SearchResult] = []
    root = Path(root)
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

        if ext_set is None or rel.suffix.lower() in ext_set:
            for lineno, line in search_file(g, keyword, ignore_case=ignore_case):
                if 0 < context < len(line):
                    line = line[:context] + "…"
                temp_out: SearchResult = {
                    "path": rel.as_posix(),
                    "lines": lineno,
                    "text": line,
                }
                out.append(temp_out)

    out = sorted(out, key=lambda h: (h["path"], h["lines"]))

    return out

URL_RE = re.compile(r"""https?://[^\s，。；！？、）】"'<>]+""")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

def find_urls(text: str) -> list[str]:
    """提取 http/https 链接，按出现顺序返回。

    - 遇到空白、中文标点（，。；！？、）、右括号、引号、尖括号就截断
    - 末尾的英文标点（. , ; : ! ? ) ] } ' " ）要去掉
    - 没有链接 → []

    Args:
        text: 用于提取http/https链接的文字

    Returns:
        提取到的http/https链接的列表，按出现顺序排序

    Raises:
        不抛异常：有错误返回空的列表
    """
    out = []
    for mo in URL_RE.finditer(text):
        url = mo.group(0).rstrip(".,;:!?)]}'\"")  # ② 再削掉末尾的英文标点
        if url:
            out.append(url)
    return out

def find_emails(text: str) -> list[str]:
    """提取邮箱，按出现顺序返回。

    - 只认 ASCII 字符（中文前缀不能被带进来）
    - 必须有"点 + 至少 2 个字母"的顶级域（a@b 不算）
    - 没有 → []

    Args:
        text: 用于提取邮箱的文字

    Returns:
        提取到的邮箱的列表，按出现顺序排序

    Raises:
        不抛异常：有错误返回空的列表
    """
    out = []
    for mo in EMAIL_RE.finditer(text):
        email = mo.group(0)
        if email:
            out.append(email)
    return out

def write_atomic(path: Path, text: str) -> None:
    """原子写入 UTF-8 文本。

    - 先写同目录的临时文件，再 os.replace 覆盖目标
    - 父目录不存在时自动创建
    - 结束后不能留下临时文件

    Args:
        path: 要写入的文件地址
        text: 要写入的文件内容

    Returns:
        无返回值

    Raises:
        PermissionError: 目录或目标文件不可写（无权限、被独占锁定）
        OSError: 其他 I/O 错误（磁盘满、路径过长、跨盘替换等）

    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except PermissionError as e:
        raise PermissionError("目录或目标文件不可写（无权限、被独占锁定）。") from e
    except OSError:
        raise OSError("其他 I/O 错误（磁盘满、路径过长、跨盘替换等）。")


class _Checker:
    """极简断言计数器：跑完能说出 '8/8 passed'。"""

    def __init__(self) -> None:
        self.passed = 0
        self.total = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.total += 1
        self.passed += int(bool(ok))
        mark = "OK " if ok else "NG "
        extra = f"  -> {detail}" if detail and not ok else ""
        print(f"  {mark} {name}{extra}")


def _selftest() -> int:
    """离线自检：用临时目录验证四个函数，返回退出码。"""
    c = _Checker()
    tmp = Path(tempfile.mkdtemp(prefix="mytools-"))
    try:
        # ---------- 夹具 ----------
        (tmp / "sub").mkdir()
        (tmp / "a.md").write_text("hello\nPython 很有用\n", encoding="utf-8")
        (tmp / "b.txt").write_text("python 小写\n", encoding="utf-8")
        (tmp / "sub" / "c.md").write_text("nested Python\n", encoding="utf-8")
        (tmp / "bin.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 8)

        # ---------- 8 条断言 ----------
        # ---------- 1. find_urls：削掉末尾标点 + 空输入 ----------
        urls = find_urls("见 https://a.b/c. 和 （https://x.com/y）")
        c.check("find_urls 削掉末尾句号、全角括号当边界",
                urls == ["https://a.b/c", "https://x.com/y"], str(urls))
        c.check("find_urls 空串 -> []", find_urls("") == [])

        # ---------- 2. find_emails：中文前缀不带入 + 空输入 ----------
        emails = find_emails("邮箱：张三a@b.com，还有 c@d.co")
        c.check("find_emails 不带中文前缀",
                emails == ["a@b.com", "c@d.co"], str(emails))
        c.check("find_emails 空串 -> []", find_emails("") == [])

        # ---------- 3. search_text：命中数正确（大小写敏感） ----------
        hits = search_text("Python", tmp)
        c.check("search_text 命中 2 条（b.txt 是小写 python，不该命中）",
                len(hits) == 2, f"实际 {len(hits)} 条：{[h['path'] for h in hits]}")

        # ---------- 4. search_text：排序 + 行号 + 相对路径 ----------
        first = hits[0] if hits else {}
        c.check("search_text 首条是 a.md 第 2 行",
                first.get("path") == "a.md" and first.get("lines") == 2,
                str(first))
        c.check("search_text 路径是相对路径、用 / 分隔",
                all(not Path(h["path"]).is_absolute() and "\\" not in h["path"]
                    for h in hits),
                str([h["path"] for h in hits]))

        # ---------- 5. search_text：目录不存在不崩 ----------
        c.check("search_text 目录不存在 -> []",
                search_text("Python", "这个目录不存在") == [])

        # ---------- 6. search_text：空关键词 ----------
        c.check("search_text 空关键词 -> []", search_text("", tmp) == [])

        # ---------- 7. write_atomic：自动建父目录 + 内容正确 ----------
        target = tmp / "deep" / "nested" / "out.txt"
        write_atomic(target, "原子写入\n")
        c.check("write_atomic 自动建父目录并写入",
                target.exists() and target.read_text(encoding="utf-8") == "原子写入\n",
                f"exists={target.exists()}")

        # ---------- 8. write_atomic：不留 .tmp 残留 ----------
        leftovers = [p.name for p in tmp.rglob("*.tmp")]
        c.check("write_atomic 没留下 .tmp 残留", leftovers == [], str(leftovers))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{c.passed}/{c.total} passed")
    return 0 if c.passed == c.total else 1

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)          # 没有参数时打印用法
