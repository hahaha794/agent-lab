#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D1 验收脚本：检查 w3_d1_paths.py 的四个函数是否符合约定。

用法：
    python w3_d1_check.py            # 检查 w3_d1_paths.py
    python w3_d1_check.py 别的模块名   # 检查其他模块

它会自己建一个临时夹具目录（_w3d1_fixture），跑完自动删掉，不碰你的 notes/。
"""

from __future__ import annotations

import importlib
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
FIXTURE = BASE / "_w3d1_fixture"


# ---------------------------------------------------------------- 夹具
def build_fixture() -> Path:
    """造一个结构固定的目录树，所有断言都基于它。"""
    if FIXTURE.exists():
        shutil.rmtree(FIXTURE)

    (FIXTURE / "sub" / "deep").mkdir(parents=True)
    (FIXTURE / "skipme").mkdir()

    (FIXTURE / "a.md").write_text("a" * 12, encoding="utf-8")
    (FIXTURE / "b.txt").write_text("b" * 20, encoding="utf-8")
    (FIXTURE / "sub" / "c.md").write_text("c" * 30, encoding="utf-8")
    (FIXTURE / "sub" / "deep" / "d.md").write_text("d" * 40, encoding="utf-8")
    (FIXTURE / "skipme" / "e.md").write_text("e" * 50, encoding="utf-8")
    (FIXTURE / "pic.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 4)

    # 并列深度用的第二个夹具：x/yy/z.md 与 a/bb/c.md 深度相同
    tie = FIXTURE / "_tie"
    (tie / "x" / "yy").mkdir(parents=True)
    (tie / "a" / "bb").mkdir(parents=True)
    (tie / "x" / "yy" / "z.md").write_text("z", encoding="utf-8")
    (tie / "a" / "bb" / "c.md").write_text("c", encoding="utf-8")
    return FIXTURE


# ---------------------------------------------------------------- 断言框架
class Checker:
    def __init__(self) -> None:
        self.passed = 0
        self.total = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.total += 1
        self.passed += int(bool(ok))
        mark = "✅" if ok else "❌"
        print(f"  {mark} {name}{('  →  ' + detail) if detail else ''}")

    def summary(self) -> int:
        print(f"\n{self.passed}/{self.total} 通过")
        if self.passed == self.total:
            print("D1 验收通过 🎉")
            return 0
        print("把 ❌ 的条目逐条修掉再来一次。")
        return 1


def rel(p: Path, root: Path) -> str:
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return str(p)


# ---------------------------------------------------------------- 主流程
def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    mod_name = argv[0] if argv else "w3_d1_paths"

    try:
        module = importlib.import_module(mod_name)
    except ModuleNotFoundError:
        print(f"找不到模块 {mod_name}.py —— 先按练习题把四个函数写出来。")
        return 2
    except Exception as exc:  # 模块里 import 阶段就崩了
        print(f"导入 {mod_name} 失败：{type(exc).__name__}: {exc}")
        return 2

    missing = [n for n in ("list_files", "summarize", "deepest", "describe")
               if not hasattr(module, n)]
    if missing:
        print(f"{mod_name}.py 缺少函数：{', '.join(missing)}")
        return 2

    root = build_fixture()
    c = Checker()
    try:
        # ---------- 1. list_files：基本情况 ----------
        files = module.list_files(root)
        got = sorted(rel(p, root) for p in files)
        expect_all = ["a.md", "b.txt", "pic.jpg", "sub/c.md", "sub/deep/d.md",
                      "skipme/e.md", "_tie/a/bb/c.md", "_tie/x/yy/z.md"]
        c.check("list_files 返回所有文件（8 个）", len(files) == 8, f"实际 {len(files)}")
        c.check("list_files 不含目录", all(Path(p).is_file() for p in files))
        c.check("list_files 结果稳定可排序", got == sorted(got))

        # ---------- 2. list_files：排除目录 ----------
        files2 = module.list_files(root, {"skipme"})
        rels2 = {rel(p, root) for p in files2}
        c.check("list_files 能排除 skipme", not any("skipme" in r for r in rels2))
        c.check("list_files 排除后剩 7 个", len(files2) == 7, f"实际 {len(files2)}")

        # ---------- 3. list_files 边界 ----------
        empty = root / "_empty"
        empty.mkdir(exist_ok=True)
        c.check("空目录 → 返回空列表", module.list_files(empty) == [])
        c.check("不存在的目录 → 返回空列表",
                module.list_files(root / "这个不存在") == [])

        # ---------- 4. summarize ----------
        target = module.list_files(root, {"skipme", "_tie"})
        info = module.summarize(target)
        c.check("summarize 返回 dict", isinstance(info, dict))
        c.check("summarize.count = 5", info.get("count") == 5, f"实际 {info.get('count')}")
        # a.md 12 + b.txt 20 + sub/c.md 30 + sub/deep/d.md 40 + pic.jpg 8 = 110
        total = info.get("total_bytes")
        c.check("summarize.total_bytes = 110（整数 110，不是 '110.00B'）",
                total == 110,
                f"实际 {total!r}（类型 {type(total).__name__}）")
        by = info.get("by_suffix") or {}
        c.check("by_suffix 统计正确",
                by.get(".md") == 3 and by.get(".txt") == 1 and by.get(".jpg") == 1,
                f"实际 {by}")

        # ---------- 5. deepest ----------
        deep = module.deepest(target, root)
        c.check("deepest 找到 sub/deep/d.md",
                deep is not None and rel(Path(deep), root) == "sub/deep/d.md",
                f"实际 {rel(Path(deep), root) if deep else None}")

        tie_root = root / "_tie"
        tie_files = module.list_files(tie_root)
        tie_deep = module.deepest(tie_files, tie_root)
        c.check("deepest 深度并列时取字典序最小的 a/bb/c.md",
                tie_deep is not None and rel(Path(tie_deep), tie_root) == "a/bb/c.md",
                f"实际 {rel(Path(tie_deep), tie_root) if tie_deep else None}")
        c.check("deepest 空列表 → None", module.deepest([], root) is None)

        # ---------- 6. describe ----------
        d = module.describe(root / "sub" / "deep" / "d.md")
        c.check("describe 返回 dict", isinstance(d, dict))
        c.check("describe.name = d.md", d.get("name") == "d.md", f"实际 {d.get('name')!r}")
        c.check("describe.stem = d", d.get("stem") == "d", f"实际 {d.get('stem')!r}")
        c.check("describe.suffix = .md", d.get("suffix") == ".md", f"实际 {d.get('suffix')!r}")
        c.check("describe.parent = deep", d.get("parent") == "deep", f"实际 {d.get('parent')!r}")

        # ---------- 7. 代码卫生 ----------
        src = (BASE / f"{mod_name}.py").read_text(encoding="utf-8", errors="ignore")
        c.check("没有用 str + \"/\" 拼路径", '"/" +' not in src and "\\\" + \\\"" not in src)
        c.check("有 encoding=\"utf-8\"（或没读文件则跳过）",
                "open(" not in src or "encoding" in src)

        return c.summary()
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
