#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D4 验收脚本：检查 w3_d4_regex.py 的五个函数。

用法：
    python w3_d4_check.py            # 检查 w3_d4_regex.py
    python w3_d4_check.py 别的模块名

D4 是纯正则处理，全部是函数级断言，不需要夹具目录。
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent


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
            print("D4 验收通过 🎉")
            return 0
        print("把 ❌ 的条目逐条修掉再来一次。")
        return 1


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    mod_name = argv[0] if argv else "w3_d4_regex"

    try:
        m = importlib.import_module(mod_name)
    except ModuleNotFoundError:
        print(f"找不到模块 {mod_name}.py —— 先按练习题把五个函数写出来。")
        return 2
    except Exception as exc:
        print(f"导入 {mod_name} 失败：{type(exc).__name__}: {exc}")
        return 2

    need = ("find_urls", "find_emails", "find_dates", "mask_phones", "split_by_separators")
    missing = [n for n in need if not hasattr(m, n)]
    if missing:
        print(f"{mod_name}.py 缺少函数：{', '.join(missing)}")
        return 2

    c = Checker()

    # ---------------- 1. find_urls ----------------
    text = "访问 https://example.com/a?x=1，或 http://test.org/p. 以及 https://a.b/c) 结束"
    urls = m.find_urls(text)
    c.check("find_urls 从混合文本里提取 3 条",
            urls == ["https://example.com/a?x=1", "http://test.org/p", "https://a.b/c"],
            str(urls))
    c.check("find_urls 去掉末尾的句号", m.find_urls("见 https://example.com.") == ["https://example.com"],
            str(m.find_urls("见 https://example.com.")))
    c.check("find_urls 不被全角括号污染", m.find_urls("（https://x.com/y）") == ["https://x.com/y"],
            str(m.find_urls("（https://x.com/y）")))
    c.check("find_urls 没有链接 → []", m.find_urls("这里没有链接") == [])
    c.check("find_urls 返回 list[str]",
            isinstance(urls, list) and all(isinstance(u, str) for u in urls))

    # ---------------- 2. find_emails ----------------
    emails = m.find_emails("联系 a.b@example.com 或 c@x.co，也可以 d@mail.co.uk")
    c.check("find_emails 提取 3 条（含子域）",
            emails == ["a.b@example.com", "c@x.co", "d@mail.co.uk"], str(emails))
    c.check("find_emails 不把中文前缀带进邮箱",
            m.find_emails("邮箱：张三a@b.com") == ["a@b.com"],
            str(m.find_emails("邮箱：张三a@b.com")))
    c.check("find_emails 缺顶级域 → []", m.find_emails("不是邮箱：a@b") == [],
            str(m.find_emails("不是邮箱：a@b")))
    c.check("find_emails 纯文本 → []", m.find_emails("没有邮箱") == [])

    # ---------------- 3. find_dates ----------------
    dates = m.find_dates("2026-11-20 和 2026-13-01 和 2026-00-10 和 2026-11-32")
    c.check("find_dates 只留合法日期（13 月 / 00 月 / 32 日都排除）",
            dates == ["2026-11-20"], str(dates))
    c.check("find_dates 允许 01 月 和 31 日",
            m.find_dates("2026-01-31") == ["2026-01-31"], str(m.find_dates("2026-01-31")))
    c.check("find_dates 允许 12 月 和 01 日",
            m.find_dates("2026-12-01") == ["2026-12-01"])
    c.check("find_dates 格式不对（斜杠）→ []",
            m.find_dates("2026/11/20") == [], str(m.find_dates("2026/11/20")))
    c.check("find_dates 空文本 → []", m.find_dates("") == [])

    # ---------------- 4. mask_phones ----------------
    masked = m.mask_phones("电话 13812345678 和 19900001111")
    c.check("mask_phones 保留前 3 后 4，中间替换成 ****",
            masked == "电话 138****5678 和 199****1111", repr(masked))
    c.check("mask_phones 12 位数字不动（\\b 的作用）",
            m.mask_phones("138123456789") == "138123456789",
            repr(m.mask_phones("138123456789")))
    c.check("mask_phones 不是 1 开头的 11 位不动",
            m.mask_phones("23812345678") == "23812345678")
    c.check("mask_phones 没有号码时原样返回",
            m.mask_phones("没有电话") == "没有电话")

    # ---------------- 5. split_by_separators ----------------
    parts = m.split_by_separators("a, b;c，d；e  f")
    c.check("split_by_separators 处理半角/全角/空白分隔",
            parts == ["a", "b", "c", "d", "e", "f"], str(parts))
    c.check("split_by_separators 空串 → []", m.split_by_separators("") == [])
    c.check("split_by_separators 全是分隔符 → []",
            m.split_by_separators(" ,;，； ") == [], str(m.split_by_separators(" ,;，； ")))
    c.check("split_by_separators 没有分隔符 → 整段一个元素",
            m.split_by_separators("abc") == ["abc"])

    # ---------------- 6. 代码卫生 ----------------
    src = (BASE / f"{mod_name}.py").read_text(encoding="utf-8", errors="ignore")
    c.check("使用了 re 模块", "import re" in src)
    c.check("没有裸 except:", "except:" not in src)
    missing_doc = [n for n in need if not (getattr(m, n).__doc__ or "").strip()]
    c.check("五个函数都有 docstring", not missing_doc, f"缺少：{missing_doc}")
    c.check("没有用 str.split 硬拆 URL（提示：URL 里也有冒号斜杠）",
            "://" in src or "https?" in src, "看起来没写 URL 的正则")

    return c.summary()


if __name__ == "__main__":
    sys.exit(main())
