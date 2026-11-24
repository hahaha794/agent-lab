#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re

URL_RE = re.compile(r"""https?://[^\s，。；！？、）】"'<>]+""")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
DATE_RE = re.compile(r"\b\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])\b")
PHONE_RE = re.compile(r"\b1[3-9]\d{9}\b")
SEP_RE = re.compile(r"[,;，；\s]+")

def find_urls(text: str) -> list[str]:
    """提取 http/https 链接，按出现顺序返回。

    - 遇到空白、中文标点（，。；！？、）、右括号、引号、尖括号就截断
    - 末尾的英文标点（. , ; : ! ? ) ] } ' " ）要去掉
    - 没有链接 → []
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
    """
    out = []
    for mo in EMAIL_RE.finditer(text):
        email = mo.group(0)
        if email:
            out.append(email)
    return out

def find_dates(text: str) -> list[str]:
    """提取 YYYY-MM-DD，并【校验】范围：月 01-12、日 01-31。

    - 2026-13-01（13 月）、2026-00-10（00 月）、2026-11-32（32 日）都不算
    - 没有 → []
    """
    out = []
    for mo in DATE_RE.finditer(text):
        date = mo.group(0)
        if date:
            out.append(date)
    return out

def mask_phones(text: str) -> str:
    """把 11 位手机号（1 开头、第二位 3-9）的中间四位换成 ****。

    - 13812345678 → 138****5678
    - 长度不是正好 11 位的（如 12 位）不能动
    """
    return PHONE_RE.sub(lambda mo: mo.group(0)[:3] + "****" + mo.group(0)[-4:], text)

def split_by_separators(text: str) -> list[str]:
    """按半角/全角逗号、分号、空白切分，丢掉空串。

    - "a, b;c，d；e" → ["a","b","c","d","e"]
    - 空串 / 全是分隔符 → []
    """
    return [t for t in SEP_RE.split(text) if t]
