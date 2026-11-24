#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path

import w3_d5_search

def normalize_exts(exts: Iterable[str] | None = None) -> set[str] | None:
    return {e.lower().lstrip(".") for e in exts} if exts else None

def main()->int:
    parser = argparse.ArgumentParser(description='目录关键词搜索')
    parser.add_argument('keyword',help='关键词')
    parser.add_argument('--dir',type=Path,default=Path("."),help='搜索目录（默认.）')
    parser.add_argument('--ext',type=str,action="append",default=[],help='只搜这些后缀；md 和 .md 都认')
    parser.add_argument('--ignore-case',action="store_true",help='大小写不敏感')
    parser.add_argument('--context',type=int,default=0,help='命中行超过 N 字符时截断（0 = 不截）')
    parser.add_argument('--json',action="store_true",help='输出 JSON')
    args = parser.parse_args()

    print(f"准备搜索 {args.dir},关键词 {args.keyword}")

    if not args.dir.is_dir():
        print(f"错误:目录不存在或不是目录: {args.dir}", file=sys.stderr)
        return 2

    ext_set = normalize_exts(args.ext)
    results = w3_d5_search.search_dir(args.dir, args.keyword, args.ignore_case, ext_set)
    if not results:
        print(f"未命中", file=sys.stderr)
        return 1
    summarize = w3_d5_search.summarize_hits(results)
    if args.json:
        hits = [{"path": str(p), "line": n, "text": t} for p, n, t in results]
        out = {
            "keyword": args.keyword,
            "dir": str(args.dir),
            "files": summarize['files'],
            "matches": summarize['matches'],
            "hits": hits,
        }
        print(json.dumps(out,ensure_ascii=False,indent=2))
        return 0
    else:
        for hit_path, lineno, line in results:
            print(w3_d5_search.format_hit(hit_path, lineno, line, args.context))
        print("---")
        print(f"命中{summarize['files']}个文件，{summarize['matches']}处")
        return 0

if __name__ == "__main__":
    sys.exit(main())