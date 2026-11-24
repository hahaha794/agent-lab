# todo.py 逐段解析

> 对象：`C:\Users\admin\Desktop\study\todo.py`（349 行，第 1 周交付物）
> 目标：把每一段代码"为什么这么写""运行时会发生什么"讲透，顺带说清每个 import 的用途。
> 建议边看边把文件打开对照，不要只读这份文档。

---

## 0. 先把它跑起来（真实输出）

```powershell
cd "C:\Users\admin\Desktop\study"
.\.venv\Scripts\Activate.ps1
python todo.py --selftest
```

```
✅ 自检通过：增 / 删 / 改 / 查、持久化、损坏降级、中文往返 全部正常。
```

```powershell
python todo.py
```

```
数据文件：C:\Users\admin\Desktop\study\todos.json

---------------- 待办清单 ----------------
  1) 添加      2) 查看      3) 完成
  4) 删除      5) 清空已完成       q) 退出
------------------------------------------
请选择 > 2
[ ]   1  做数学题  (2026-11-04 17:29)
共 1 条，已完成 0 条，未完成 1 条。
```

下面所有讲解都建立在这份代码上。

---

## 1. 整体结构：一个文件、五层

```
┌─────────────────────────────────────────────────┐
│ 五、入口        main() / __main__ 保护            │  ← 决定"跑什么模式"
├─────────────────────────────────────────────────┤
│ 四、自检        selftest()                        │  ← 断言，验证下面四层
├─────────────────────────────────────────────────┤
│ 三、交互层      interactive / read_line / parse_id│  ← 处理人的输入输出
├─────────────────────────────────────────────────┤
│ 二、业务层      add / find / mark_done / remove ...│  ← 只改内存，不碰磁盘
├─────────────────────────────────────────────────┤
│ 一、持久化层    load_todos / save_todos           │  ← 只碰磁盘，不懂业务
└─────────────────────────────────────────────────┘
```

**为什么这么分层？** 因为它们的"依赖方向"是单向的：

- 持久化层**不知道**待办是什么，只知道"一个列表 ⇄ 一个 JSON 文件"；
- 业务层**不知道**磁盘，只操作内存里的列表；
- 交互层**不知道** JSON，只负责"读一行字 → 调业务函数 → 决定存不存"；
- 入口只负责选模式。

好处很实在：想加一个"网页版"，只要换掉交互层，下面两层原样复用；想换存储（改成 SQLite），只改第一层，上面全不动。这是最小的"可替换"设计，也是第 8 周之后加人工审批、加工具调用的基础。

**数据流：**

```
磁盘 todos.json
     │  load_todos()
     ▼
内存 list[dict] ──► 业务函数改它 ──► save_todos() ──► 磁盘 todos.json
     ▲                                                    │
     └──────────────── 下次启动再读 ◄─────────────────────┘
```

---

## 2. 逐段讲解

### 2.1 文件头（第 1–22 行）

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行待办清单（第 1 周交付物）：增删改查 + JSON 持久化。..."""
```

| 行 | 作用 | 说明 |
|---|---|---|
| `#!/usr/bin/env python3` | shebang | 这是给 Linux/macOS 用的"用哪个解释器跑"。**Windows 上完全无效**，留着是为了以后放到服务器上能 `./todo.py` 直接执行。 |
| `# -*- coding: utf-8 -*-` | 编码声明 | Python 3 默认就是 UTF-8，这行其实是历史习惯。留着无害，好处是老编辑器/老工具也知道怎么读。 |
| `"""..."""` 模块 docstring | 模块说明 | 这是**唯一能被 `help(todo)` 和 IDE 悬停读到**的注释。文件级说明必须写在这里，不能写成 `# 注释`。 |

docstring 里写了四件事：数据结构长什么样、怎么用、三条用法示例、四条设计要点。**写 docstring 的标准就是这个：让没看过代码的人 30 秒内知道怎么用。**

`数据结构（todos.json）::` 后面那个 `::` 是 reStructuredText 的语法，表示"下面是一个代码块"，IDE 会把它渲染成等宽字体。

### 2.2 import 区（第 23–32 行）

```python
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
```

**没有一个是第三方库。** 9 行 import 里，1 行是"语法开关"，另外 8 行全是 Python 自带的标准库。

| import | 在本文件里干什么 | 具体用在哪 |
|---|---|---|
| `from __future__ import annotations` | **不是模块，是语法开关**：让所有类型注解"只当字符串存着，不立即求值" | 全文件的 `list[Todo]`、`Todo \| None`。有了它，Python 3.8 也能写 `list[dict]` 这种新式注解 |
| `argparse` | 解析命令行参数 | `main()` 里解析 `--selftest`、`--file` |
| `json` | JSON 序列化/反序列化 | `load_todos` 的 `json.load`，`save_todos` 的 `json.dump` |
| `os` | 操作系统接口 | `os.fdopen`（把文件描述符包成文件对象）、`os.fsync`（强制落盘）、`os.replace`（原子替换）、`os.getpid`（取进程号） |
| `sys` | 解释器相关 | `sys.stderr`（错误输出到标准错误）、`sys.exit`（设退出码） |
| `tempfile` | 创建临时文件 | `tempfile.mkstemp`（原子写的第一步） |
| `datetime` | 时间 | `datetime.now().isoformat(...)` 生成创建时间 |
| `pathlib.Path` | 面向对象的路径 | `DATA_FILE`、`path.open()`、`path.parent`、`path.unlink()` |
| `typing.Any` | 类型注解占位 | `Todo = dict[str, Any]` |

**为什么 import 要按这个顺序排？** PEP 8 规定的分组顺序：`__future__` → 标准库 → 第三方库 → 本项目模块，组间空一行。本文件没有第三方库，所以只有前两组。

### 2.3 模块级常量（第 34–42 行）

```python
Todo = dict[str, Any]

DATA_FILE = Path(__file__).resolve().parent / "todos.json"

MENU = """
---------------- 待办清单 ----------------
  1) 添加      2) 查看      3) 完成
  4) 删除      5) 清空已完成       q) 退出
------------------------------------------"""
```

**`Todo = dict[str, Any]`** —— 类型别名。下面所有 `list[Todo]` 读起来就像"待办列表"，比 `list[dict[str, Any]]` 直观。注意它**只在类型检查层面有意义**，运行时 `Todo` 就是 `dict`，不做任何校验（想真校验要用 `pydantic` 或 `dataclass`）。

**`DATA_FILE = Path(__file__).resolve().parent / "todos.json"`** —— 这一行值得单独讲，它同时修掉了两个经典 bug：

```
__file__            = 当前 .py 文件路径（可能相对，如 'todo.py'）
   .resolve()       = 转成绝对路径，且解开符号链接
   .parent          = 取所在目录 → C:\Users\admin\Desktop\study
   / "todos.json"   = 用 / 拼路径（pathlib 的运算符重载，跨平台）
```

- 如果写成 `open("todos.json")`，路径是**相对于"当前工作目录"**的。你在 `study` 下运行没问题，一旦从别的目录 `python C:\...\study\todo.py`，它就会去那个目录找/建文件 —— 数据"消失"。
- 用 `__file__` 定位，**文件永远跟着脚本走**。

**`MENU`** —— 三引号字符串，开头有个换行（所以菜单前会空一行），结尾**没有**换行（`print(MENU)` 会自动补一个）。菜单用常量而不是每轮临时拼，好处是改文案只改一处。

### 2.4 `load_todos()`（第 50–73 行）：把"读失败"全部变成正常值

```python
def load_todos(path: Path = DATA_FILE) -> list[Todo]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as exc:
        print(f"[警告] ...", file=sys.stderr)
        return []
    except OSError as exc:
        print(f"[错误] ...", file=sys.stderr)
        return []
    ...
```

**逐行看运行时会发生什么：**

1. `path.open("r", encoding="utf-8")` —— 以只读 + UTF-8 打开。**`encoding` 必须写**：Windows 上不写就用系统默认编码（简体中文环境是 GBK），遇到 UTF-8 的中文会 `UnicodeDecodeError`。
2. `with` —— 代码块结束（包括异常退出）时自动 `close()`，不会漏关文件句柄。
3. `json.load(f)` —— 一次性读完、解析成 Python 对象。**空文件会抛 `JSONDecodeError`，不是返回 `None`**，这是最容易误判的一点。

**三个 except 的顺序有讲究：**

```
FileNotFoundError  ⊂ OSError        ← 必须先捕，否则被 OSError 抢走
JSONDecodeError    ⊂ ValueError     ← 和 OSError 互不包含，顺序无所谓
```

`except` 是"从上往下第一个匹配的生效"，所以子类必须写在父类前面。

**为什么全部 `return []` 而不是让它崩？** 这是产品决策，不是技术约束：

- 文件不存在 → 第一次使用，本来就该是空列表（正常情况）；
- 文件损坏 → 崩掉会让用户连"看看还有什么"都做不到；降级成空列表 + 警告，至少程序能开；
- 代价是"数据看起来丢了"——所以必须往 `sys.stderr` 打警告，不能静默。

**注意 `print(..., file=sys.stderr)`**：错误信息走"标准错误"而不是"标准输出"。这样你把正常输出重定向到文件时（`python todo.py > out.txt`），警告仍然会显示在屏幕上。

**第 69–73 行是"类型防护"：**

```python
if not isinstance(data, list):
    return []
return [t for t in data if isinstance(t, dict) and "id" in t and "text" in t]
```

`json.load` 只保证"是合法 JSON"，不保证"是我要的形状"。文件里如果是 `{"a": 1}`（字典）或 `"abc"`（字符串），后面 `for t in todos` 就会以 `TypeError` 之类崩掉。所以：

- 顶层不是 `list` → 判为损坏；
- 列表里混进非字典、或缺 `id`/`text` 的脏记录 → 用列表推导式过滤掉（"尽量救，不整体放弃"）。

### 2.5 `save_todos()`（第 76–102 行）：为什么保存要写 20 行

这是全文件最"超纲"的一段，但它是**区分玩具和工具的地方**。

```python
try:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".todos-", suffix=".tmp", dir=str(path.parent))
except OSError as exc:
    ...
    return False
```

1. `path.parent.mkdir(parents=True, exist_ok=True)` —— 保证目录存在。`parents=True` 表示"上级目录一起建"，`exist_ok=True` 表示"已存在不算错"。这样 `--file D:\data\x\todos.json` 也能用。
2. `tempfile.mkstemp(...)` —— 在**同一个目录**下创建一个唯一名字的临时文件，返回 `(文件描述符 fd, 路径)`。
   - `dir=` 必须指向目标文件所在目录：**`os.replace` 只有在同一个磁盘卷内才是原子操作**，跨盘会退化成"复制 + 删除"，就不安全了。
   - 名字以 `.` 开头：Linux/macOS 上隐藏；`prefix`/`suffix` 让人一眼看出这是什么文件。

```python
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)
```

3. `os.fdopen(fd, "w", ...)` —— `mkstemp` 给的是**文件描述符**（一个整数），`fdopen` 把它包成正常的文件对象。`with` 结束时它会 `close()`，同时也关掉 `fd`。
4. `json.dump(..., ensure_ascii=False, indent=2)` —— `False` 让中文原样写（否则变成 `\u4e73` 这种转义，能读但没法看）；`indent=2` 让文件带缩进，人能读、diff 也好看。
5. `f.write("\n")` —— 补一个结尾换行。很多工具（git、编辑器）把"文件末尾有换行"当作良好格式。
6. `f.flush()` —— 把 Python 缓冲区的内容推给操作系统。
7. `os.fsync(f.fileno())` —— 把操作系统的缓存**真正写进磁盘**。没有这一步，断电时"你以为写了"的数据可能还在内存里。
8. `os.replace(tmp_path, path)` —— **原子替换**：要么目标文件还是旧的，要么已经是新的，不存在"写了一半"的中间态。

**核心思想：先写旁边的新文件，全部落盘后再"啪"一下换过去。** 直接 `open(path, "w")` 的话，打开那一刻旧文件已经被清空，后面任何一步失败，数据就永久没了。

**失败路径（第 97–100 行）：**

```python
except (OSError, TypeError) as exc:
    Path(tmp_path).unlink(missing_ok=True)   # 清掉半成品
    print(f"[错误] 保存失败：{exc}", file=sys.stderr)
    return False
```

- `OSError`：磁盘满、文件被占用、权限不足；
- `TypeError`：列表里混进了不能序列化的对象。**你的更早一版就踩过这个坑**：`created_at` 直接存 `datetime.now()`，`json.dump` 当场抛 `TypeError: Object of type datetime is not JSON serializable`。现在改成字符串（`isoformat`），问题消失；
- `unlink(missing_ok=True)`：删临时文件，文件不存在也不报错（Python 3.8+）。

**为什么返回 bool 而不是抛异常？** 因为调用方只想区分"成了/没成"，交互层据此决定要不要打印"已添加"。真要排查原因，`stderr` 里已经有完整原因。这属于"把异常降级成返回值"的常见取舍——注意代价：**忘了检查返回值就会静默失败**，所以本文件每一处 `save_todos(...)` 都放在 `if` 里。

### 2.6 `next_id()`（第 110–112 行）

```python
def next_id(todos: list[Todo]) -> int:
    return max((t.get("id", 0) for t in todos), default=0) + 1
```

- `(t.get("id", 0) for t in todos)` 是**生成器表达式**，不是列表推导式——不占内存，`max` 边算边丢。
- `default=0`：空列表时 `max()` 会抛 `ValueError: max() arg is an empty sequence`，`default` 让空列表返回 0，于是第一条 id = 1。
- `.get("id", 0)`：脏数据里没有 `id` 时当 0 处理，不崩。

**为什么用"最大值 +1"而不是"长度 +1"？**

```
列表 [1, 2, 3]，删掉 2 → 长度 2 → 新 id = 3  ← 和已存在的 3 撞车！
最大值 +1      → 3 + 1 = 4              ← 永远不撞
```

**为什么删掉的 id 不复用？** 用户刚看到"3 号是买菜"，删掉后又加一条变成 3 号，会以为是同一条。id 是"身份证号"，一旦发出去就不回收。

> 边界情况（诚实说明）：如果 `todos.json` 里 id 是字符串 `"5"`，`max` 会在 `str` 和 `int` 之间比较而抛 `TypeError`。本文件的 `load_todos` 只检查了"有没有 id"，没检查类型，所以这是个已知的窄边界。

### 2.7 `add_todo()`（第 115–124 行）

```python
def add_todo(todos: list[Todo], text: str) -> Todo:
    todo: Todo = {
        "id": next_id(todos),
        "text": text.strip(),
        "done": False,
        "created_at": datetime.now().isoformat(timespec="minutes"),
    }
    todos.append(todo)
    return todo
```

- **只在内存里追加，不写盘**。这是刻意的：业务函数保持"纯"（除了改传进来的列表），写盘由交互层决定。好处是单元测试不用碰磁盘，坏处是调用方可能忘存。
- `text.strip()` 去掉首尾空格。**为什么在业务层再 strip 一次**？因为交互层检查的是 `text.strip()` 是否为空，但传进来的是原始 `text`。在这里统一 strip，能保证"不管谁调用，存进去的都是干净的"。
- `isoformat(timespec="minutes")` → `"2026-11-04T17:30"`，是 ISO 8601 格式：**能被 `datetime.fromisoformat` 解析回来、字符串排序等于时间排序**。这比自定义格式好在"标准"。
- `todos.append(todo)` 是**原地修改**，函数外面那个列表一起变——因为 `list` 是可变对象，传的是引用。
- 返回新那条，方便调用方打印 `#{todo['id']}`。

### 2.8 `find_todo()`（第 127–132 行）

```python
for todo in todos:
    if todo.get("id") == todo_id:
        return todo
return None
```

线性扫描，O(n)。几十条待办无所谓；几千条就该用 `{id: todo}` 字典索引了。

返回的是**列表里那个字典的引用**，所以调用方拿着它改字段，列表里那条也跟着变——`mark_done` 正是利用这一点。

找不到返回 `None`，而不是抛异常或返回 `{}`：`None` 在 Python 里就是"没有"，`if todo is None` 语义最清楚。

### 2.9 `mark_done()`（第 135–141 行）

```python
todo = find_todo(todos, todo_id)
if todo is None:
    return False
todo["done"] = True
return True
```

- 复用 `find_todo`，不重复写循环（DRY）。
- 验证了返回值再改，避免 `None['done']` 的 `TypeError`。
- **改完不 save**：docstring 里明确写了"改完要调用方自己 save"。业务层不管持久化。
- 用 `is None` 而不是 `== None`：后者在自定义 `__eq__` 的对象上可能有意外行为，PEP 8 明确要求 `is None`。

### 2.10 `remove_todo()`（第 144–155 行）：`del t` 为什么是错的

```python
remain = [t for t in todos if t.get("id") != todo_id]
if len(remain) == len(todos):
    return False
todos[:] = remain
return True
```

**先看你之前的写法为什么无效：**

```python
for t in todos:
    if t['id'] == todo_id:
        del t          # ← 只删掉了"名字 t"，列表里那个字典还在
```

`del` 删除的是**变量绑定**，不是对象。循环变量 `t` 每轮被重新赋值，`del t` 效果等于"下一轮再赋值一次"。列表 `todos` 一个元素都没少。

**再看"边遍历边删"的坑：**

```python
# 假设 todos = [1, 2, 3]，要删 2
for i, t in enumerate(todos):
    if t['id'] == 2:
        todos.remove(t)   # 删掉后列表变成 [1, 3]，索引前移
```

删除后剩余元素整体前移，循环索引继续 +1，导致**紧跟在被删元素后面那条被跳过**。这类 bug 不会报错，只在特定数据下出现。

**现在的写法为什么安全：**

1. 列表推导式**先造一个新列表**，遍历的是原列表、写的是新列表，互不干扰；
2. `len(remain) == len(todos)` → 一条都没少 → 说明没找到 → 返回 False，不用额外 `any()`；
3. `todos[:] = remain` —— **切片赋值，原地替换**。

第 3 点是关键，对比一下：

```python
todos = remain      # ← 重新绑定：函数外那个列表还是旧的，改动全丢
todos[:] = remain   # ← 原地替换：函数外持有的同一个列表对象内容变了
```

因为函数参数是"对象的引用按值传递"，重新赋值只改本地名字。切片赋值保留同一个列表对象，调用方的 `todos` 跟着变。

### 2.11 `format_todo()`（第 158–161 行）

```python
mark = "x" if todo.get("done") else " "
return f"[{mark}] {todo.get('id'):>3}  {todo.get('text', '')}  ({todo.get('created_at', '-')})"
```

- 三元表达式 `A if 条件 else B`，比四行 `if/else` 紧凑。
- `{todo.get('id'):>3}` 里的 `:>3` 是**格式规范**：`>` 右对齐、宽度 3。所以 `1` 显示成 `  1`，`42` 显示成 ` 42`，编号列能对齐。
- 全部用 `.get(...)` 带默认值：脏数据缺字段时打印 `''` 或 `-`，而不是 `KeyError`。
- **注意引号**：外层双引号、内层单引号。如果写成 `f'...{t['id']}...'`，只有 Python 3.12+ 才合法，3.11 及以前直接 `SyntaxError`。

输出长这样：

```
[ ]   1  做数学题  (2026-11-04 17:29)
[x]   2  写周报    (2026-11-04 17:31)
```

### 2.12 `print_all()`（第 164–172 行）

```python
if not todos:
    print("还没有待办，输入 1 添加一条。")
    return
for todo in todos:
    print(format_todo(todo))
done = sum(1 for t in todos if t.get("done"))
print(f"共 {len(todos)} 条，已完成 {done} 条，未完成 {len(todos) - done} 条。")
```

- 空列表时**早点 return**（guard clause），避免后面还要判空。
- `sum(1 for t in todos if t.get("done"))` —— 用 `sum` 数布尔值。因为 `True == 1`，所以"统计满足条件的个数"可以这么写；等价的 `len([t for t in todos if ...])` 会多造一个列表。
- 统计行给用户"全局感"，避免反复上下翻。

### 2.13 `read_line()`（第 180–185 行）

```python
try:
    return input(prompt)
except (EOFError, KeyboardInterrupt):
    return None
```

把"读一行"包起来，统一处理两种"人不想继续了"：

- `EOFError`：标准输入被关闭（管道读完、IDE 停止运行、Ctrl+D）；
- `KeyboardInterrupt`：Ctrl+C。

返回 `None` 表示"没读到有效输入"，让调用方决定怎么退出——**而不是在这里直接 `sys.exit()`**。这样这个函数既能用在交互里，也能被测试替身换掉（`selftest` 之外的那次测试就是这么做的）。

### 2.14 `parse_id()`（第 188–197 行）

```python
raw = raw.strip()
if not raw:
    return None
try:
    return int(raw)
except ValueError:
    print(f"“{raw}” 不是数字编号。")
    return None
```

- 空输入（直接回车）**静默返回 None**，不打印抱怨——用户可能就是想跳过。
- 非数字打印提示并返回 None。
- `int()` 还能吃 `" 12 "`、`"+12"`、`"0x10"`？不能，`int("0x10")` 会 `ValueError`；`int("１２")`（全角）也失败。这是可接受的。

**为什么不在这里判断"编号是否存在"？** 因为那是业务层的职责（`mark_done` 返回值）。分层原则：交互层只管"输入格式对不对"。

### 2.15 `interactive()`（第 200–265 行）：主循环

```python
todos = load_todos(path)     # ← 只在进入时读一次
print(f"数据文件：{path}")
while True:
    print(MENU)
    raw = read_line("请选择 > ")
    ...
```

**每次操作后的调用链（以"添加"为例）：**

```
read_line() → "1" → choice="1"
  read_line("要做什么：") → "买牛奶"
  判空 → add_todo(todos, "买牛奶")          [内存 +1 条]
  save_todos(todos, path)                    [写临时文件 → fsync → 替换]
  成功 → print("已添加 #1：买牛奶")
        → 回到 while 顶部，重新画菜单
```

**几个细节：**

- `choice = raw.strip().lower()`：`"Q"`、`" q "` 都能退出；中文"退出"不受 `lower()` 影响。
- `if choice in {"q", "quit", "exit", "退出"}`：用集合而不是四个 `or`，查找 O(1) 且更好读。
- 每个分支里 `read_line` 返回 `None`（EOF/Ctrl+C）都要单独处理——因为这是在"二级提示"里退出，不能直接掉到 `else`。
- `if not text.strip(): continue`：`continue` 回到 `while` 顶部，重新画菜单。
- `if save_todos(...)` 才打印成功：**存盘失败时不会骗你说"已添加"**（失败原因已经在 `stderr`）。
- 选择 5 用 `todos[:] = [...]` 原地过滤，和 `remove_todo` 是同一个套路。
- 所有分支都是 `if/elif`，末尾 `else` 兜住非法选项。

**一个诚实的说明**：如果 `save_todos` 失败，内存里已经加进去的那条仍然在，只是没落盘；继续操作会带着"幽灵数据"跑，下次启动它又消失。更严谨的做法是失败时回滚内存（保存前先复制一份）。这里为了可读性没做——知道有这回事就行。

### 2.16 `selftest()`（第 273–326 行）

```python
path = DATA_FILE.parent / f".todos-selftest-{os.getpid()}.json"
try:
    ... 7 组断言 ...
finally:
    path.unlink(missing_ok=True)
```

- 用**独立文件名**（带进程号），不污染真实 `todos.json`，也不会两个进程同时跑时打架。
- `try/finally`：**不管断言成功还是失败**都删临时文件。如果用 `with tempfile.TemporaryDirectory()` 更省事，但在当前沙箱里新建子目录会挂（详见第 5.1 节），所以改成"直接在当前目录放一个临时文件"。
- `assert 条件, "错误信息"`：条件为假时抛 `AssertionError`，进程退出码非 0。
- 7 组断言覆盖了：文件不存在、id 递增、保存成功、重开后还在、标记完成、找不到的 id、删除、重复删除、id 不复用、非法 JSON、顶层非列表、空文件、中文往返。

**注意一个坑**：`python -O todo.py --selftest` 会**跳过所有 assert**（`-O` 优化模式），自检变成"什么都没检查但显示通过"。生产项目一般用 `pytest` 的 `assert`（重写过，不受 `-O` 影响），或者显式 `if not 条件: raise`。

**为什么自检要写在文件里，而不是另开 `test_todo.py`？** 这个项目只有 349 行，把自检内联方便"拿到就能验证"。等文件大到 500 行以上，就该拆成 `pytest` 测试文件了。

### 2.17 `main()`（第 334–345 行）

```python
parser = argparse.ArgumentParser(description="命令行待办清单")
parser.add_argument("--selftest", action="store_true", help="离线自检，不碰真实数据")
parser.add_argument("--file", type=Path, default=DATA_FILE, help=...)
args = parser.parse_args(argv)
if args.selftest:
    return selftest()
return interactive(args.file)
```

- `action="store_true"`：不带值，出现即为 `True`。
- `type=Path`：自动把字符串转成 `Path`，还能在参数非法时报错。
- `default=DATA_FILE`：**默认参数在 `add_argument` 执行时求值一次**（模块加载时 `DATA_FILE` 已经算好），所以没问题。如果这里写的是 `default=Path("todos.json")`，就会又变成"相对当前目录"的老 bug。
- `--file` 的 `dest` 自动是 `file`，所以后面用 `args.file`。
- 参数 `argv` 默认 `None` → `parse_args` 自动读 `sys.argv[1:]`；显式传列表就能在测试里模拟命令行。
- 返回 `int` 退出码，0 = 成功。

### 2.18 `if __name__ == "__main__":`（第 348–349 行）

```python
if __name__ == "__main__":
    sys.exit(main())
```

- **直接运行**时 `__name__ == "__main__"`，调用 `main()`；
- **被别的文件 import** 时 `__name__ == "todo"`，不执行——这样别人可以 `from todo import load_todos` 复用你的函数，而不会一导入就跑起菜单。

`sys.exit(main())`：把 `main()` 的返回值变成进程退出码。成功 0，失败非 0，shell/CI 才判断得出"这次跑挂了没有"。等价写法 `raise SystemExit(main())`。

---

## 3. 一次性把"运行时发生了什么"串起来

**`python todo.py` 的完整时序：**

| 阶段 | 发生的事 | 内存 | 磁盘 |
|---|---|---|---|
| 1 | 解释器读文件、编译成字节码 | — | 读 `todo.py` |
| 2 | 执行 import | 加载 json/argparse 等模块 | 读标准库 |
| 3 | 执行模块级代码：`Todo`、`DATA_FILE`、`MENU` 赋值 | 三个常量就位 | — |
| 4 | 定义 8 个函数（**只定义，不执行**） | 函数对象就位 | — |
| 5 | `__name__ == "__main__"` 成立 → 调 `main()` | — | — |
| 6 | `parse_args()` 解析 `[]`（无参数） | args.selftest=False | — |
| 7 | 调 `interactive(DATA_FILE)` → `load_todos()` | `todos = [...]` | **读** `todos.json` |
| 8 | 进入 `while`，打印菜单，等输入 | — | — |
| 9 | 用户选 1 → `add_todo` → `save_todos` | 列表 +1 | **写**临时文件 → fsync → replace |
| 10 | 选 q → `return 0` → `sys.exit(0)` | 释放 | — |

**关掉再打开会怎样？** 第 7 步重新执行 `load_todos()`，读的就是第 9 步 `os.replace` 换上去的那个文件——所以数据还在。**你上一版之所以"关掉就没了"，就是因为第 9 步写的是另一个文件名。**

---

## 4. 设计取舍问答（看懂这些才算真懂）

**Q1：为什么不用 `class Todo` 或 `@dataclass`？**
A：349 行的脚本，用 `dict` 最直接：`json` 原生支持、调试时 `print` 就能看、不用写 `to_dict()`。代价是没有字段校验（拼错 `"txet"` 不报错）。等字段超过 5 个、或需要类型检查时，换 `dataclass` 是自然演进。

**Q2：为什么业务层不写盘，非要调用方自己 save？**
A：让业务函数"纯"，才能被单独测试、被批处理（比如一次导入 100 条只存一次盘）、将来被 Web 接口复用（请求结束统一提交）。代价是"忘记 save"会静默丢数据——所以交互层每个分支都显式调用了。

**Q3：为什么错误打印到 `stderr`，正常输出到 `stdout`？**
A：Unix 惯例。`python todo.py > out.txt` 只重定向正常输出，错误仍然显示在终端；反过来 `2>/dev/null` 只屏蔽错误。日志/config 才有这种区分。

**Q4：为什么 `remove_todo` 不直接 `todos.remove(t)`？**
A：因为要找的那条是"按 id 匹配"，`list.remove(x)` 是按**值相等**删除，得先拿到对象；而且删除过程中会二次遍历。列表推导式一次遍历、逻辑最清楚。

**Q5：为什么 `load_todos` 有 `path: Path = DATA_FILE` 这个默认参数？**
A：让"正常使用"和"测试/自定义路径"共用一个函数。注意：**默认参数在函数定义时求值一次**，对 `Path` 这种不可变对象安全；如果默认值是 `[]` 或 `{}`，所有调用会共享同一个对象——这是 Python 最经典的坑之一。

**Q6：为什么 `todos[:] = remain` 而不 `return remain`？**
A：两种都能用，但"原地改 + 返回 bool"让调用方少写一行赋值，且不会出现"忘了接收返回值"的 bug。代价是函数有副作用——docstring 里写清楚就行。

**Q7：为什么自检里要专门测"坏文件"？**
A：因为真实世界里最常见的事故就是文件坏了（手改错、磁盘满、程序崩溃）。**测试的价值不在"正常路径"，在"异常路径"**。

---

## 5. 库的说明

### 5.1 先说结论：`todo.py` 零第三方依赖

```powershell
pip list          # 装了什么都不影响 todo.py
pip uninstall 全部第三方库 → todo.py 照样能跑
```

这就是为什么它能"拿到就运行"——只用了 Python 自带的**标准库**。这也是命令行小工具的常态：依赖越少，越不容易在别人机器上装不上。

下面逐个说这 9 行 import 的用途（含容易忽略的细节），再补充说明本项目**其他脚本**用到的第三方库。

### 5.2 标准库逐个说明

#### `json` —— 数据的"通用语言"

```python
json.load(f)          # 文件 → Python 对象（list/dict/str/int/float/bool/None）
json.dump(todos, f, ensure_ascii=False, indent=2)   # Python 对象 → 文件
```

- 作用：把内存里的 `list[dict]` 变成一行行可读文本，再变回来。**所有 API 收发、所有配置文件，基本都是 JSON**，第 5 周调大模型时你会天天见到它。
- 关键参数：
  - `ensure_ascii=False`：中文原样输出；默认 `True` 会把中文转成 `\u4e73`，程序没错但人看不懂。
  - `indent=2`：缩进美化，方便人读和 git diff。
- 能序列化的类型只有 6 种：`dict/list/str/int/float/bool/None`。**`datetime` 不行**——你上一版就是在 `created_at` 里塞了 `datetime.now()`，`json.dump` 直接 `TypeError`。要么转成字符串（本文件的做法），要么写 `default=` 转换函数。

#### `pathlib` —— 路径操作

```python
Path(__file__).resolve().parent / "todos.json"
path.parent
path.open("r", encoding="utf-8")
path.unlink(missing_ok=True)
```

- 作用：把"路径字符串拼接"变成面向对象操作。`"a" + "\\" + "b"` 在 Windows/macOS 上不一样，`Path("a") / "b"` 自动用对分隔符。
- `resolve()`：转绝对路径 + 解开符号链接（`__file__` 可能是相对路径）。
- `parent`：上级目录。
- `unlink(missing_ok=True)`：删文件，不存在也不报错。
- 对比老写法 `os.path.join`：`pathlib` 更不容易拼错，且 `path.open()` 把编码参数放在同一个调用里。

#### `os` —— 底层文件操作

```python
os.fdopen(fd, "w", encoding="utf-8")
os.fsync(f.fileno())
os.replace(tmp_path, path)
os.getpid()
```

- `fdopen`：`tempfile.mkstemp` 返回的是**文件描述符**（整数），不是文件对象；`fdopen` 把它包成能用 `with` 的文件对象。
- `fsync`：强制把操作系统缓存刷到磁盘。注释里说的"断电也不丢"就靠它。
- `replace`：**原子**重命名/替换。同一磁盘卷内是原子的——这是"要么旧、要么新"的技术保证。
- `getpid`：取当前进程号，给自检的临时文件起唯一名字。

#### `tempfile` —— 临时文件

```python
fd, tmp_path = tempfile.mkstemp(prefix=".todos-", suffix=".tmp", dir=str(path.parent))
```

- 作用：安全地创建"名字不会冲突"的临时文件（内部用 `O_CREAT | O_EXCL` 原子创建，多进程同时跑也不会撞名）。
- 三个参数：`prefix`/`suffix` 控制文件名长什么样，`dir` 控制放哪。**`dir` 必须是目标目录**，否则跨盘替换就不原子了。

#### `sys` —— 解释器接口

```python
sys.stderr
sys.exit(main())
```

- `stderr`：错误输出流。和 `stdout` 分开，才能"正常输出存文件、错误留在屏幕"。
- `exit(code)`：结束进程并设退出码。`0` 成功，非 0 失败。CI/脚本靠它判断成败。

#### `argparse` —— 命令行参数

```python
parser.add_argument("--selftest", action="store_true")
parser.add_argument("--file", type=Path, default=DATA_FILE)
```

- 作用：把 `--file x.json` 这种输入变成长度自动检查、类型自动转换、`--help` 自动生成的参数对象。
- 自己解析 `sys.argv` 也能做，但会丢掉 `--help`、报错提示、类型转换这些"免费福利"。

#### `datetime` —— 时间

```python
datetime.now().isoformat(timespec="minutes")   # "2026-11-04T17:30"
```

- `isoformat()` 输出 ISO 8601 标准格式：**能被 `fromisoformat` 解析回来、字符串排序 = 时间排序、时区信息可带可不带**。
- `timespec="minutes"` 省掉秒和微秒，文件更干净；要精确到秒就改成 `"seconds"`。
- 注意 `now()` 是**本地时间、无时区**。跨时区场景要用 `datetime.now(timezone.utc)`。

#### `typing.Any` 与 `from __future__ import annotations`

```python
Todo = dict[str, Any]
def find_todo(todos: list[Todo], todo_id: int) -> Todo | None:
```

- `Any`：告诉类型检查器"这里面什么都可能有"，避免为每个字段定义类型。
- `from __future__ import annotations`：把所有注解变成**字符串**存起来，不立即求值。这样即使运行在 Python 3.8（不支持 `list[int]`、`X | None`），代码也能正常跑。
- **类型注解不会在运行时校验任何东西**。传错类型照样跑，只是 IDE/mypy 会标红。想真校验，用 `pydantic`。

### 5.3 补充：本项目其他脚本用到的第三方库

`todo.py` 一个都不需要，但你的 `1.py` / `brain.py` / `python_study.py` 用到了下面这些。**这正是"命令行小工具"和"AI 应用"的依赖差别。**

#### `python-dotenv` —— 读取 `.env` 文件

```python
from dotenv import load_dotenv
load_dotenv()                      # .env 里的每一行 → os.environ
key = os.environ["DEEPSEEK_API_KEY"]
```

- 解决什么问题：**API Key 不能写进代码**（会随代码提交泄露），也不能在每台机器上手动设环境变量（麻烦、容易忘）。
- 原理：读 `.env` 文本文件，按 `KEY=VALUE` 解析，塞进进程的环境变量表。
- 关键事实：**Python 本身不认识 `.env`**，`open(".env")` 只能读到一堆字符串。只有 `load_dotenv()` 才会把它变成配置。
- 缺了它：`ModuleNotFoundError: No module named 'dotenv'`——你在 `todo.py` 第 4 行已经撞过一次。
- 用在哪：`1.py:6`、`brain.py:4`、`python_study.py:4`

#### `requests` —— 发 HTTP 请求

```python
r = requests.get("https://api.open-meteo.com/v1/forecast", params={...}, timeout=10)
data = r.json()
```

- 解决什么问题：用几行代码调别人的网页接口，自动处理 URL 编码、连接池、超时、JSON 解析。
- 用在哪：`brain.py:6`，`get_weather()` 用它调两个免费的 open-meteo 接口（先地名→经纬度，再经纬度→天气）。
- 缺了它：`brain.py` 第 6 行直接崩，天气工具不可用。
- 注意：**调 DeepSeek 不需要 `requests`**。`openai` 库内部自带 HTTP 客户端（你这个 venv 里是 `httpx2`）。`requests` 只在你**手动调第三方 API** 时才需要。

#### `openai` —— 调大模型的客户端

```python
from openai import OpenAI
client = OpenAI(api_key=..., base_url=...)
client.chat.completions.create(model="deepseek-chat", messages=[...], tools=[...])
```

- 解决什么问题：封装"发请求 + 拼 JSON + 解析返回 + 处理流式/工具调用"的全部细节。
- 妙处：**几乎所有国产模型都兼容这套接口**（DeepSeek、通义、智谱、Kimi），换服务商只改 `base_url` 和 `model` 两行。
- 用在哪：`1.py`、`brain.py`、`python_study.py`（通过 LangChain）。
- 关键概念（第 5–8 周会用到）：`messages` 是 `list[dict]`、`tools` 是 JSON Schema 列表、返回里可能有 `tool_calls`——**模型只会"请求"调工具，真正执行的是你的代码**。

#### `pydantic` —— 数据校验

- 解决什么问题：定义"数据必须长这样"，运行时校验并给出精确错误。
- 为什么本文件提它：`Todo = dict[str, Any]` 是**假类型**，不做校验；换成 `class Todo(BaseModel)` 才能保证 `id` 是 int、`text` 是 str。
- 在你 venv 里的真实身份：它是 `openai` 的**传递依赖**（openai 用它校验 API 返回结构），你并没有直接 import 它。第 6 周做"结构化输出"时才会亲手用。

#### `langchain-core` / `langchain-openai` —— 链式编排

```python
translate_prompt | llm | parser      # LCEL 的管道语法
```

- 解决什么问题：把"提示词模板 → 模型 → 输出解析"用 `|` 串成流水线，省掉手工拼 messages。
- 用在哪：只有 `python_study.py`。
- 代价：会拉进一大堆依赖，且框架 API 变化快。路线图的建议是**第 11 周再上框架**，先手写（`brain.py` 那种）才看得懂框架替你做了什么。

### 5.4 一张总表

| 库 | 类型 | 解决什么 | 用在 | 缺了会怎样 |
|---|---|---|---|---|
| `json` `os` `sys` `pathlib` `tempfile` `datetime` `argparse` `typing` | **标准库** | 文件、路径、时间、参数、序列化 | `todo.py` | 不可能缺（随 Python 装） |
| `python-dotenv` | 第三方 | 读 `.env` → 环境变量 | 1.py / brain.py / python_study.py | `ModuleNotFoundError` |
| `requests` | 第三方 | 手动发 HTTP 请求 | brain.py | 天气工具崩 |
| `openai` | 第三方 | 调大模型 API | 1.py / brain.py / （langchain 内部） | 所有 AI 功能崩 |
| `pydantic` | 第三方（传递依赖） | 运行时数据校验 | 目前没直接用 | openai 装不上 |
| `langchain-core` / `langchain-openai` | 第三方 | 链式编排 | python_study.py | 该脚本崩 |

---

## 6. 想继续练，从这几处改

1. **加非交互模式**：`python todo.py --add "买牛奶"`、`--done 2`、`--list`，这样能写进 shell 脚本、也能被别的程序调用。
2. **换成 `dataclass`**：`@dataclass class Todo`，体会"有类型"和"没类型"的区别。
3. **加日志**：把 `print(..., file=sys.stderr)` 换成 `logging`，能输出时间戳、能分级（DEBUG/INFO/WARNING）。
4. **加并发保护**：两个终端同时写会互相覆盖，可以用文件锁（`msvcrt.locking` 或第三方 `filelock`）。
5. **拆成 `pytest`**：把 `selftest()` 里的断言搬进 `test_todo.py`，体会"测试文件"和"自检函数"的差别。
6. **加个 `requirements.txt`**：`pip freeze > requirements.txt`，让别人一条命令装齐依赖。

---

## 附：一句话总结这段代码的设计哲学

> **磁盘的事交给第一层，业务的事交给第二层，人的事交给第三层，验证交给第四层，选择交给第五层。**
> 每层只做一件事、只依赖下一层——这就是"能改得动"的代码和最容易被写成一坨 `main()` 的代码之间的全部区别。
