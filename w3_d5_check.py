#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D5 验收脚本：检查 w3_d5_search.py 的四个函数。

用法：
    python w3_d5_check.py            # 检查 w3_d5_search.py
    python w3_d5_check.py 别的模块名

夹具目录 `_w3d5_fixture` 由脚本自建、跑完自动删。
"""

from __future__ import annotations

import importlib
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
FIXTURE = BASE / "_w3d5_fixture"

A_MD = """第一行
Python 很有用
python 也很好
字面量 a.b
干扰 axb
"""
B_TXT = """无关键词
Python 出现一次
Python 第二次
"""
C_MD = "sub 里的 Python\n"
D_MD = "Python 不该被搜到\n"


def build_fixture() -> Path:
    if FIXTURE.exists():
        shutil.rmtree(FIXTURE)
    notes = FIXTURE / "notes"
    (notes / "sub").mkdir(parents=True)
    (notes / "skipme").mkdir()

    (notes / "a.md").write_text(A_MD, encoding="utf-8")
    (notes / "b.txt").write_text(B_TXT, encoding="utf-8")
    (notes / "sub" / "c.md").write_text(C_MD, encoding="utf-8")
    (notes / "skipme" / "d.md").write_text(D_MD, encoding="utf-8")
    (notes / "gbk.txt").write_bytes("Python 编码错\n".encode("gbk"))
    return notes


class Checker:
    def __init__(self) -> None:
        self.passed = 0
        self.total = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.total += 1
        self.passed += int(bool(ok))
        print(f"  {'OK ' if ok else 'NG '} {name}{('  -> ' + detail) if detail else ''}")

    def summary(self) -> int:
        print(f"\n{self.passed}/{self.total} passed")
        if self.passed == self.total:
            print("D5 验收通过")
            return 0
        print("把 NG 的条目逐条修掉再来一次。")
        return 1


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    mod_name = argv[0] if argv else "w3_d5_search"

    try:
        m = importlib.import_module(mod_name)
    except ModuleNotFoundError:
        print(f"找不到模块 {mod_name}.py —— 先按练习题把四个函数写出来。")
        return 2
    except Exception as exc:
        print(f"导入 {mod_name} 失败：{type(exc).__name__}: {exc}")
        return 2

    need = ("search_file", "search_dir", "format_hit", "summarize_hits")
    missing = [n for n in need if not hasattr(m, n)]
    if missing:
        print(f"{mod_name}.py 缺少函数：{', '.join(missing)}")
        return 2

    notes = build_fixture()
    c = Checker()
    try:
        # ---------------- 1. search_file ----------------
        c.check("search_file 区分大小写",
                m.search_file(notes / "a.md", "Python") == [(2, "Python 很有用")],
                str(m.search_file(notes / "a.md", "Python")))
        c.check("search_file ignore_case=True 命中两行",
                m.search_file(notes / "a.md", "python", ignore_case=True)
                == [(2, "Python 很有用"), (3, "python 也很好")],
                str(m.search_file(notes / "a.md", "python", ignore_case=True)))
        c.check("search_file 是字面量匹配：a.b 不命中 axb",
                m.search_file(notes / "a.md", "a.b") == [(4, "字面量 a.b")],
                str(m.search_file(notes / "a.md", "a.b")))
        c.check("search_file 读不了的 GBK 文件 -> []",
                m.search_file(notes / "gbk.txt", "Python") == [])
        c.check("search_file 不存在的文件 -> []",
                m.search_file(notes / "没有这个.md", "Python") == [])
        c.check("search_file 行内容不含行尾换行",
                all("\n" not in line for _, line in m.search_file(notes / "b.txt", "Python")))

        # ---------------- 2. search_dir ----------------
        default_hits = m.search_dir(notes, "Python")
        c.check("search_dir 默认排除规则下命中 5 处 / 4 个文件",
                len(default_hits) == 5 and len({h[0] for h in default_hits}) == 4,
                f"{len(default_hits)} 处 / {len({h[0] for h in default_hits})} 个文件")
        c.check("search_dir 结果按 (路径, 行号) 排序",
                default_hits == sorted(default_hits, key=lambda h: (h[0], h[1])),
                str([(h[0], h[1]) for h in default_hits]))
        c.check("search_dir 返回 (相对路径, 行号, 内容) 三元组",
                all(isinstance(h, tuple) and len(h) == 3 for h in default_hits))
        c.check("search_dir 路径是相对路径、用 / 分隔",
                all(not Path(h[0]).is_absolute() and "\\" not in h[0] for h in default_hits),
                str([h[0] for h in default_hits]))

        no_skip = m.search_dir(notes, "Python", excludes={"skipme"})
        c.check("search_dir excludes={'skipme'} 后剩 4 处",
                len(no_skip) == 4, str(len(no_skip)))
        c.check("search_dir 排除 skipme 后不再出现它",
                not any(h[0].startswith("skipme/") for h in no_skip))

        md_only = m.search_dir(notes, "Python", exts={".md"}, excludes={"skipme"})
        c.check("search_dir exts={'.md'} 只搜 md",
                len(md_only) == 2 and all(h[0].endswith(".md") for h in md_only),
                str([h[0] for h in md_only]))
        c.check("search_dir exts={'.MD'} 大小写不敏感",
                m.search_dir(notes, "Python", exts={".MD"}, excludes={"skipme"}) == md_only)

        c.check("search_dir 从不把 GBK 文件算进去",
                not any(h[0].endswith("gbk.txt") for h in default_hits))
        c.check("search_dir 目录不存在 -> []",
                m.search_dir(notes / "没有这个目录", "Python") == [])

        # ---------------- 3. format_hit ----------------
        c.check("format_hit 基本格式 路径:行号: 内容",
                m.format_hit("a.md", 2, "Python 很有用") == "a.md:2: Python 很有用",
                repr(m.format_hit("a.md", 2, "Python 很有用")))
        c.check("format_hit context=0 不截断",
                m.format_hit("a.md", 2, "Python 很有用", 0) == "a.md:2: Python 很有用")
        long_line = "x" * 100
        out = m.format_hit("a.md", 2, long_line, 10)
        c.check("format_hit context=10 截断并加省略号",
                out == "a.md:2: " + "x" * 10 + "…", repr(out))
        c.check("format_hit 内容正好等于 context 长度时不截断",
                m.format_hit("a.md", 2, "x" * 10, 10) == "a.md:2: " + "x" * 10)
        c.check("format_hit 内容短于 context 时不截断",
                m.format_hit("a.md", 2, "short", 10) == "a.md:2: short")

        # ---------------- 4. summarize_hits ----------------
        info = m.summarize_hits(no_skip)
        c.check("summarize_hits.files = 3（去重）", info.get("files") == 3,
                f"实际 {info.get('files')}")
        c.check("summarize_hits.matches = 4", info.get("matches") == 4,
                f"实际 {info.get('matches')}")
        c.check("summarize_hits.by_file 计数正确",
                info.get("by_file") == {"a.md": 1, "b.txt": 2, "sub/c.md": 1},
                str(info.get("by_file")))
        empty = m.summarize_hits([])
        c.check("summarize_hits 空列表 -> 全 0",
                empty == {"files": 0, "matches": 0, "by_file": {}}, str(empty))

        # ---------------- 5. 代码卫生 ----------------
        src = (BASE / f"{mod_name}.py").read_text(encoding="utf-8", errors="ignore")
        c.check("没有裸 except:", "except:" not in src)
        c.check("用 re 时必定有 re.escape（或压根没用 re）",
                not ("re.search" in src or "re.finditer" in src or "re.compile" in src)
                or "re.escape" in src,
                "用了 re 却没见 re.escape")
        missing_doc = [n for n in need if not (getattr(m, n).__doc__ or "").strip()]
        c.check("四个函数都有 docstring", not missing_doc, f"缺少：{missing_doc}")

        return c.summary()
    finally:
        shutil.rmtree(FIXTURE, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
