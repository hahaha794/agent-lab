#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D3 验收脚本：检查 w3_d3_strings.py 的五个函数。

用法：
    python w3_d3_check.py            # 检查 w3_d3_strings.py
    python w3_d3_check.py 别的模块名

D3 是纯字符串处理，不需要夹具目录，全部是函数级断言。
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
            print("D3 验收通过 🎉")
            return 0
        print("把 ❌ 的条目逐条修掉再来一次。")
        return 1


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    mod_name = argv[0] if argv else "w3_d3_strings"

    try:
        m = importlib.import_module(mod_name)
    except ModuleNotFoundError:
        print(f"找不到模块 {mod_name}.py —— 先按练习题把五个函数写出来。")
        return 2
    except Exception as exc:
        print(f"导入 {mod_name} 失败：{type(exc).__name__}: {exc}")
        return 2

    need = ("normalize_whitespace", "to_halfwidth", "split_words", "word_freq", "highlight")
    missing = [n for n in need if not hasattr(m, n)]
    if missing:
        print(f"{mod_name}.py 缺少函数：{', '.join(missing)}")
        return 2

    c = Checker()

    # ---------------- 1. normalize_whitespace ----------------
    c.check("normalize 空串 → 空串", m.normalize_whitespace("") == "")
    c.check("normalize 多个空格 → 一个",
            m.normalize_whitespace("  a   b  ") == "a b",
            repr(m.normalize_whitespace("  a   b  ")))
    c.check("normalize 把 \\n 和 \\t 也当空白",
            m.normalize_whitespace("a\n\tb") == "a b",
            repr(m.normalize_whitespace("a\n\tb")))
    c.check("normalize 处理全角空格 U+3000",
            m.normalize_whitespace("中文　全角") == "中文 全角",
            repr(m.normalize_whitespace("中文　全角")))
    c.check("normalize 不动中文字符本身",
            m.normalize_whitespace("你好，世界") == "你好，世界",
            repr(m.normalize_whitespace("你好，世界")))

    # ---------------- 2. to_halfwidth ----------------
    c.check("to_halfwidth 全角字母数字 → 半角",
            m.to_halfwidth("ＡＢＣ１２３") == "ABC123",
            repr(m.to_halfwidth("ＡＢＣ１２３")))
    c.check("to_halfwidth 全角括号 → 半角",
            m.to_halfwidth("（测试）") == "(测试)",
            repr(m.to_halfwidth("（测试）")))
    c.check("to_halfwidth 全角空格 U+3000 → 半角空格",
            m.to_halfwidth("a　b") == "a b",
            repr(m.to_halfwidth("a　b")))
    c.check("to_halfwidth 不动中文句号 U+3002",
            m.to_halfwidth("好。") == "好。",
            repr(m.to_halfwidth("好。")))
    c.check("to_halfwidth 不动中文汉字",
            m.to_halfwidth("中文") == "中文",
            repr(m.to_halfwidth("中文")))

    # ---------------- 3. split_words ----------------
    c.check("split_words 按非单词字符切分",
            m.split_words("Hello, 世界！go 123") == ["Hello", "世界", "go", "123"],
            str(m.split_words("Hello, 世界！go 123")))
    c.check("split_words 空串 → []", m.split_words("") == [])
    c.check("split_words 全是标点 → []", m.split_words("，。！？") == [],
            str(m.split_words("，。！？")))
    c.check("split_words 保留下划线（\\w 的一部分）",
            m.split_words("a_b c") == ["a_b", "c"],
            str(m.split_words("a_b c")))

    # ---------------- 4. word_freq ----------------
    freq = m.word_freq("a a b")
    c.check("word_freq 计数正确", freq == [("a", 2), ("b", 1)], str(freq))
    c.check("word_freq 忽略大小写（casefold）",
            m.word_freq("Apple apple") == [("apple", 2)],
            str(m.word_freq("Apple apple")))
    tie = m.word_freq("b a")
    c.check("word_freq 次数并列时按词字典序升序",
            tie == [("a", 1), ("b", 1)], str(tie))
    c.check("word_freq 空文本 → []", m.word_freq("") == [])
    top1 = m.word_freq("a a b c", top=1)
    c.check("word_freq top=1 只返回一个", len(top1) == 1 and top1[0] == ("a", 2), str(top1))
    c.check("word_freq 返回 list[tuple[str, int]]",
            isinstance(top1, list) and all(isinstance(w, str) and isinstance(n, int)
                                           for w, n in top1))

    # ---------------- 5. highlight ----------------
    c.check("highlight 用 【】 包裹命中",
            m.highlight("我爱北京", "北京") == "我爱【北京】",
            repr(m.highlight("我爱北京", "北京")))
    c.check("highlight 是字面量匹配：a.b 不会命中 aXb",
            m.highlight("a.b aXb", "a.b") == "【a.b】 aXb",
            repr(m.highlight("a.b aXb", "a.b")))
    c.check("highlight 处理正则元字符 a+b",
            m.highlight("a+b abb", "a+b") == "【a+b】 abb",
            repr(m.highlight("a+b abb", "a+b")))
    c.check("highlight ignore_case=True 时大小写都命中",
            m.highlight("Hello hello", "hello", ignore_case=True) == "【Hello】 【hello】",
            repr(m.highlight("Hello hello", "hello", ignore_case=True)))
    c.check("highlight ignore_case=False 时只命中大小写一致的",
            m.highlight("Hello hello", "hello") == "Hello 【hello】",
            repr(m.highlight("Hello hello", "hello")))
    c.check("highlight 空关键词 → 原样返回（不能无限插入）",
            m.highlight("abc", "") == "abc",
            repr(m.highlight("abc", "")))
    c.check("highlight 没命中 → 原样返回",
            m.highlight("abc", "zzz") == "abc",
            repr(m.highlight("abc", "zzz")))

    # ---------------- 6. 代码卫生 ----------------
    src = (BASE / f"{mod_name}.py").read_text(encoding="utf-8", errors="ignore")
    c.check("没有裸 except:", "except:" not in src)
    missing_doc = [n for n in need if not (getattr(m, n).__doc__ or "").strip()]
    c.check("五个函数都有 docstring", not missing_doc, f"缺少：{missing_doc}")

    return c.summary()


if __name__ == "__main__":
    sys.exit(main())
