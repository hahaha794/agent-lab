import argparse
import sys
import json
from pathlib import Path

EXCLUDED = {".venv", "__pycache__", ".git", ".idea"}

def is_excluded(file: Path, root: Path) -> bool:
    """文件是否位于要跳过的目录里。

    提示：file.relative_to(root) 得到相对路径，它的 .parts 是各级目录名，
          只要有任何一段在 EXCLUDED 里就该跳过。
    """
    # TODO: 3 行以内
    parts = file.relative_to(root).parts
    return any(part in EXCLUDED for part in parts)

def human_size(num_bytes: float) -> str:
    """把字节数转换成人类易读的字符串，如 75.8 KB / 1.2 MB。"""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"

def normalize_ext(raw: str) -> str:
    """把用户输入的扩展名统一成 '.py' 这种形式。"""
    ext = raw.strip().lower()          # 去空格、转小写
    if ext.startswith("*"):            # 去掉 *.py 里的 *
        ext = ext[1:]
    if not ext.startswith("."):        # 没有点就补上
        ext = "." + ext
    return ext

def parse_size(raw: str) -> int:
    """把 1MB / 512KB / 1024 这样的写法解析成字节数。

    用作 argparse 的 type= 参数：解析失败时抛 ArgumentTypeError，
    argparse 会自动报错并以退出码 2 结束，不用自己写校验。
    """
    text = raw.strip().upper().replace(" ", "")
    units = {"B": 0, "KB": 1, "MB": 2, "GB": 3, "TB": 4}

    i = 0
    while i < len(text) and (text[i].isdigit() or text[i] in ".+-"):
        i += 1
    num_part, unit = text[:i], text[i:]
    if unit == "":
        unit = "B"
    if unit not in units:
        raise argparse.ArgumentTypeError(f"不认识的单位：{raw}（可用 B/KB/MB/GB/TB）")

    try:
        value = float(num_part)
    except ValueError:
        raise argparse.ArgumentTypeError(f"不认识的数字：{raw}") from None
    if value < 0:
        raise argparse.ArgumentTypeError("大小不能为负")
    return int(value * 1024 ** units[unit])

def main(argv: list[str] | None = None)-> int:
    parser = argparse.ArgumentParser(description="统计目录下的文件数量和大小")
    parser.add_argument("--dir", type = Path,
                        default = None, help = "要统计的目录（默认当前目录）")
    parser.add_argument("--ext", type = str, default = None, help = "只统计这个扩展名")
    parser.add_argument("--top", type = int, default= 3, help = "按大小降序列出前N个")
    parser.add_argument("--json",action = "store_true", help = "把结果用JSON格式打印" )
    parser.add_argument("--dry-run", action = "store_true",help = "只打印计划，不扫描")

    #新增 parse_size()：把 1MB / 512KB / 1.5gb / 1024 解析成字节数，非法输入抛 ArgumentTypeError
    parser.add_argument("--min-size", type = parse_size, default = 0,
                        help = "只统计大于等于该大小的文件，如 1MB / 512KB")
    parser.add_argument("--max-size", type = parse_size, default = 0,
                        help = "只统计小于等于该大小的文件，如 10MB（0 表示不限）")
    args = parser.parse_args(argv)

    root = (args.dir or Path(".")).resolve()
    if not root.is_dir():  # ← 校验
        print(f"目录不存在：{root}", file=sys.stderr)
        return 1

    ext = normalize_ext(args.ext) if args.ext else None

    if args.dry_run:
        plan = {
            "dry_run": True,
            "dir": str(root),
            "ext": ext,
            "min_size": args.min_size,
            "max_size": args.max_size,
            "top_n": args.top,
            "excluded": sorted(EXCLUDED),
            "count": 0,
            "top": [],
        }
        if args.json:
            print(json.dumps(plan, indent=4, ensure_ascii=False))
        else:
            print("== 扫描计划（--dry-run，未执行扫描）==")
            print(f"目录：{plan['dir']}")
            print(f"扩展名：{ext or '不限'}")
            print(f"大小下限：{human_size(args.min_size) if args.min_size else '不限'}")
            print(f"大小上限：{human_size(args.max_size) if args.max_size else '不限'}")
            print(f"排除目录：{', '.join(plan['excluded'])}")
            print(f"列出前 {args.top} 个")
        return 0

    files: list[tuple[Path, int]] = []
    for f in root.rglob("*"):  # ← 只扫一次
        if not f.is_file():
            continue
        if is_excluded(f, root):
            continue
        if ext and f.suffix.lower() != ext:  # ← 相等，不是 in
            continue
        size = f.stat().st_size
        if size < args.min_size:                     # ← 大小下限（字节）
            continue
        if args.max_size and size > args.max_size:   # ← 大小上限，0 表示不限
            continue
        files.append((f, size))
    total = sum(size for _, size in files)
    num_files = len(files)
    sum_size = human_size(total)
    sorted_files = sorted(files, key=lambda x: x[1], reverse=True)

    if args.json:
        top_items = [
            {"path": str(p), "relative": p.relative_to(root).as_posix(), "size": s}
            for p, s in sorted_files[:args.top]
        ]
        a = {
            "dir": str(root),
            "count": num_files,
            "total_bytes": total,
            "total_human": sum_size,
            "top": top_items,
        }
        print(json.dumps(a, indent=4, ensure_ascii=False))
        return 0
    print(f"扫描目录：{root}")
    print(f"文件数：{num_files}")
    print(f"总大小：{sum_size}")
    if not files:
        print("没有匹配的文件。")
        return 0
    print(f"最大的 {args.top} 个：")
    for path, size in sorted_files[:args.top]:
        print(f"  {human_size(size):>10}  {path.relative_to(root)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())