#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D2 验收脚本：检查 w3_d2_read.py 的五个函数。

用法：
    python w3_d2_check.py            # 检查 w3_d2_read.py
    python w3_d2_check.py 别的模块名

夹具目录 `_w3d2_fixture` 由脚本自建、跑完自动删，不碰你的 notes/。
"""

from __future__ import annotations

import importlib
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
FIXTURE = BASE / "_w3d2_fixture"


def build_fixture() -> tuple[Path, Path]:
    """返回 (data 目录, out 目录)。

    读写测试用 data/，写文件测试用 out/ —— 两者分开，避免测试互相污染。
    """
    if FIXTURE.exists():
        shutil.rmtree(FIXTURE)

    data = FIXTURE / "data"
    out = FIXTURE / "out"
    (data / "sub").mkdir(parents=True)
    (data / "skipme").mkdir()
    out.mkdir()

    (data / "a.md").write_text("第一行\n第二行\n", encoding="utf-8")       # 2 行，最长 3
    (data / "b.txt").write_text("hello world", encoding="utf-8")          # 1 行，无结尾换行，11
    (data / "sub" / "c.md").write_text("a\nbb\nccc\n", encoding="utf-8")  # 3 行，最长 3
    (data / "empty.md").write_text("", encoding="utf-8")                  # 0 行
    (data / "skipme" / "e.md").write_text("skip me\n", encoding="utf-8")
    (data / "pic.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 8)     # 非 UTF-8
    (data / "gbk.txt").write_bytes("中文内容\n".encode("gbk"))              # GBK
    return data, out


class Checker:
    def __init__(self) -> None:
        self.passed = 0
        self.total = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.total += 1
        self.passed += int(bool(ok))
        print(f"  {'✅' if ok else '❌'} {name}{('  →  ' + detail) if detail else ''}")

    def summary(self) -> int:
        print(f"\n{self.passed}/{self.total} 通过")
        if self.passed == self.total:
            print("D2 验收通过 🎉")
            return 0
        print("把 ❌ 的条目逐条修掉再来一次。")
        return 1


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    mod_name = argv[0] if argv else "w3_d2_read"

    try:
        module = importlib.import_module(mod_name)
    except ModuleNotFoundError:
        print(f"找不到模块 {mod_name}.py —— 先按练习题把五个函数写出来。")
        return 2
    except Exception as exc:
        print(f"导入 {mod_name} 失败：{type(exc).__name__}: {exc}")
        return 2

    need = ("read_text_safe", "count_lines", "longest_line", "write_atomic", "scan_dir")
    missing = [n for n in need if not hasattr(module, n)]
    if missing:
        print(f"{mod_name}.py 缺少函数：{', '.join(missing)}")
        return 2

    data, out = build_fixture()
    c = Checker()
    try:
        # ---------- 1. read_text_safe ----------
        text = module.read_text_safe(data / "a.md")
        c.check("read_text_safe 能读出 UTF-8 文本", text == "第一行\n第二行\n", repr(text)[:40])
        c.check("read_text_safe 遇到二进制 → None",
                module.read_text_safe(data / "pic.jpg") is None)
        c.check("read_text_safe 遇到 GBK 文件 → None",
                module.read_text_safe(data / "gbk.txt") is None)
        c.check("read_text_safe 遇到不存在的文件 → None（不抛异常）",
                module.read_text_safe(data / "没有这个.txt") is None)

        # ---------- 2. count_lines ----------
        c.check("count_lines 空文件 = 0", module.count_lines(data / "empty.md") == 0,
                f"实际 {module.count_lines(data / 'empty.md')}")
        c.check("count_lines 两行文件 = 2", module.count_lines(data / "a.md") == 2,
                f"实际 {module.count_lines(data / 'a.md')}")
        c.check("count_lines 末尾无换行也算 1 行", module.count_lines(data / "b.txt") == 1,
                f"实际 {module.count_lines(data / 'b.txt')}")
        c.check("count_lines 三行文件 = 3", module.count_lines(data / "sub" / "c.md") == 3,
                f"实际 {module.count_lines(data / 'sub' / 'c.md')}")

        # ---------- 3. longest_line ----------
        c.check("longest_line 取最长（并列取第一条）",
                module.longest_line(data / "a.md") == "第一行",
                repr(module.longest_line(data / "a.md")))
        c.check("longest_line 去掉行尾换行",
                module.longest_line(data / "b.txt") == "hello world",
                repr(module.longest_line(data / "b.txt")))
        c.check("longest_line 空文件 = 空字符串",
                module.longest_line(data / "empty.md") == "")

        # ---------- 4. write_atomic（一律写在 out/ 里） ----------
        target = out / "x.txt"
        module.write_atomic(target, "第一行\nsecond\n")
        c.check("write_atomic 写出的内容可原样读回",
                target.read_text(encoding="utf-8") == "第一行\nsecond\n",
                repr(target.read_text(encoding="utf-8"))[:40])
        module.write_atomic(target, "覆盖后的内容\n")
        c.check("write_atomic 覆盖后内容正确",
                target.read_text(encoding="utf-8") == "覆盖后的内容\n")
        leftovers = [p.name for p in out.rglob("*.tmp")]
        c.check("write_atomic 没留下临时文件", leftovers == [], str(leftovers))
        nested = out / "deep" / "y.txt"
        module.write_atomic(nested, "nested\n")
        c.check("write_atomic 能自动建父目录", nested.exists(),
                "父目录不存在时会抛 FileNotFoundError")

        # ---------- 5. scan_dir（只看 data/，与 out/ 无关） ----------
        info = module.scan_dir(data, {"skipme"})
        c.check("scan_dir 返回 dict", isinstance(info, dict))
        c.check("scan_dir.files = 4（跳过二进制和 GBK）", info.get("files") == 4,
                f"实际 {info.get('files')}")
        c.check("scan_dir.lines = 6（2+1+3+0）", info.get("lines") == 6,
                f"实际 {info.get('lines')}")
        c.check("scan_dir.longest_len = 11", info.get("longest_len") == 11,
                f"实际 {info.get('longest_len')}")
        c.check("scan_dir.longest_file = b.txt", info.get("longest_file") == "b.txt",
                f"实际 {info.get('longest_file')!r}")
        skipped = info.get("skipped") or []
        c.check("scan_dir.skipped 含 gbk.txt 和 pic.jpg",
                set(skipped) == {"gbk.txt", "pic.jpg"}, f"实际 {skipped}")
        c.check("scan_dir 不包含 skipme 里的文件",
                not any("skipme" in str(s) for s in skipped))
        empty_info = module.scan_dir(data / "没有这个目录")
        c.check("scan_dir 目录不存在 → 全 0，不抛异常",
                empty_info.get("files") == 0 and empty_info.get("lines") == 0)

        # ---------- 6. 代码卫生 ----------
        src = (BASE / f"{mod_name}.py").read_text(encoding="utf-8", errors="ignore")
        c.check("有 open( 就必有 encoding", "open(" not in src or "encoding" in src)
        c.check("没有把整个文件读进内存再数行（用 for line in f）",
                ".read().splitlines()" not in src and ".read().split(" not in src)

        return c.summary()
    finally:
        shutil.rmtree(FIXTURE, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
