#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re

def normalize_whitespace(text: str) -> str:
    """把连续的空白字符压成一个半角空格，并去掉首尾空白。

    - 空白包括：空格、\\t、\\n、\\r、全角空格 U+3000
    - 空串 → ""
    """
    return re.sub(r"\s+", " ", text).strip()

def to_halfwidth(text: str) -> str:
    """全角转半角。

    - U+FF01 ~ U+FF5E（全角 ASCII）→ 减去 0xFEE0
    - U+3000（全角空格）→ 半角空格
    - 其他字符（含中文汉字、中文句号 U+3002）原样保留
    """
    out = []
    for char in text:
        code = ord(char)
        if 0xFF01 <= code <= 0xFF5E:
            out.append(chr(code - 0xFEE0))
        elif code == 0x3000:
            out.append(" ")
        else:
            out.append(char)
    return "".join(out)

def split_words(text: str) -> list[str]:
    """按"非单词字符"切分，丢掉空串。

    - 单词字符 = 正则 \\w：字母、数字、下划线、中文
    - 全是标点 → []
    """
    return [t for t in re.split(r"[^\w]+", text) if t]

def word_freq(text: str, top: int = 10) -> list[tuple[str, int]]:
    """词频 Top N。

    - 用 split_words 切词，统一 casefold()（Apple 和 apple 算同一个）
    - 排序：次数降序；次数相同按词字典序升序
    - 空文本 → []
    """
    counts = {}
    for word in split_words(text):
        key = word.casefold()
        counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top]

def highlight(text: str, keyword: str, ignore_case: bool = False) -> str:
    """把命中的关键词用 【】 包起来。

    - 关键词按【字面量】处理（a.b 只匹配 a.b，不匹配 axb）
    - keyword 为空 → 原样返回 text
    - 没命中 → 原样返回 text
    """
    if not keyword:
        return text
    flags = re.IGNORECASE if ignore_case else 0
    return re.sub(re.escape(keyword),  # ② 关键词当字面量
                  lambda mo: f"【{mo.group(0)}】",  # ③ 保留原始大小写
                  text, flags=flags)