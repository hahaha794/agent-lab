#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

def human_size(n: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    i = 0
    size = float(n)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{int(size)} B" if i == 0 else f"{size:.2f} {units[i]}"


def list_files(root: Path, excludes: set[str] | None = None) -> list[Path]:
    """递归收集 root 下所有【文件】（不含目录）。

    - 任何一段路径名出现在 excludes 里的文件，跳过
    - root 不存在 / 不是目录 → 返回 []
    - 返回值按 str(p) 排序（保证每次运行顺序一致）
    """
    files: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if excludes:
            rel_parts = p.relative_to(root).parts
            if any(part in excludes for part in rel_parts):
                continue
        files.append(p)
    return sorted(files,key=lambda p: str(p))


def summarize(files: list[Path]) -> dict:
    """返回 {"count": int, "total_bytes": int, "by_suffix": {后缀: 数量}}。

    - 后缀统一小写（".MD" 要算成 ".md"）
    - 没有后缀的文件，key 是空字符串 ""
    """
    count = len(files)
    total_bytes = 0
    by_suffix: dict[str, int] = {}
    for p in files:
        total_bytes += p.stat().st_size
        suffix = p.suffix.lower()
        by_suffix[suffix] = by_suffix.get(suffix, 0) + 1
    return {"count": count, "total_bytes": total_bytes, "by_suffix": by_suffix}

def deepest(files: list[Path], root: Path) -> Path | None:
    """返回相对 root 层级最深的那一条。

    - 深度 = len(p.relative_to(root).parts)
    - 深度并列时，取 str(p) 字典序最小的
    - 空列表 → None
    """
    if not files:
        return None

    def key(p: Path) -> tuple[int, str]:
        try:
            rel = p.relative_to(root)
        except ValueError:
            raise ValueError(f"deepest(): {p} 不在 {root} 之下") from None
        return -len(rel.parts), str(p)

    return min(files, key=key)

def describe(p: Path) -> dict:
    """返回 {"name": str, "stem": str, "suffix": str, "parent": str}。

    - parent 是【父目录的名字】，不是完整路径
    """
    return {"name": p.name, "stem": p.stem, "suffix": p.suffix, "parent": p.parent.name}

if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent
    a = list_files(ROOT / "notes")
    summary = summarize(a)
    deepest_file = deepest(a, Path("notes"))
    print(f"==notes目录报告==\n"
          f"文件数：{summary['count']}\n"
          f"总大小：{human_size(summary['total_bytes'])}")
    by_suffix_1 = summary["by_suffix"]
    for i, (k, v) in enumerate(by_suffix_1.items()):
        if i == 0:
            print(f"后缀分布：{k}×{v}")
        else:
            print(f"     {k}×{v}")
    print(f"最深路径：{deepest_file}（深度{len(deepest_file.relative_to(Path("notes")).parts)}）")
