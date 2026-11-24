# todo.py 代码评审报告

> 评审对象：`C:\Users\admin\Desktop\study\todo.py`（评审时 62 行，已备份为 `todo.py.bak`）
> 评审标准：能否放进真实开发环境（会被别人读、会出错、会长期维护）
> 结论：**22 个问题**，其中 5 个会导致"数据静默丢失/功能完全无效"（P0），8 个影响健壮性（P1），9 个是规范与可维护性（P2）。

---

## 一、P0：会让程序行为错误，而且不报错

### 1. `save()` 写错了文件 —— 数据永远存不住

```python
# todo.py.bak:19
with open('DATA_FILE','w', encoding='utf-8') as f:   # ← 带引号
```

`'DATA_FILE'` 是字符串字面量，不是变量。`load()` 读 `todos.json`，`save()` 却写到名为 `DATA_FILE` 的文件里，两边不是同一个文件。

**后果**（已在你的目录里实证）：你之前添加的「做数学题」落在了 `study\DATA_FILE` 里，而程序启动时读的是 `todos.json` → 每次启动都是空列表 → 加完就"丢"。

**修复**：`open(DATA_FILE, ...)`，`DATA_FILE` 用 `Path(__file__).resolve().parent / "todos.json"` 定义。

> 这是最危险的一类 bug：不抛异常、不出错、只是数据静静地不见了。

### 2. `remove()` 根本没删掉任何东西

```python
# todo.py.bak:44-47
for t in todos:
    if t['id'] == todo_id:
        del t          # ← 删的是循环变量名，不是列表元素
```

`del t` 只解除了 `t` 这个名字的绑定，列表里的字典一个都没少。而且即使改成 `todos.remove(t)`，边遍历边删会跳过下一条。

**修复**：列表推导式重建，再原地替换：

```python
remain = [t for t in todos if t.get("id") != todo_id]
if len(remain) == len(todos):
    return False
todos[:] = remain      # 原地替换，外部持有的列表对象继续有效
return True
```

### 3. `mark_done()` 永远返回 False，且不写盘

```python
# todo.py.bak:35-40
for t in todos:
    if t['id'] == todo_id:
        t['done'] = True
return False            # ← 找到也返回 False；而且没有 save()
```

内存改了、返回值错、磁盘没动 → 重开就还原。

### 4. `remove()` 同样不写盘、返回值恒为 False

删完不 `save()`，等价于没删。

### 5. `main()` 每次输入都重新读盘

```python
# todo.py.bak:54-55
todos = load()
add(todos, text)
```

每轮循环都把文件重新读一遍。表面没问题，实际掩盖了"保存失败"：一旦某次 `save()` 失败，下一轮 `load()` 会把它悄悄覆盖回去，用户完全察觉不到数据没写进去。

**修复**：进循环前 `load()` 一次，之后只操作内存，改动后显式 `save()`。

---

## 二、P1：功能缺失或一遇异常就崩

| # | 位置 | 问题 | 修复 |
|---|---|---|---|
| 6 | `main` | 只有「添加 / 退出」，**缺查看、完成、删除** —— 不满足"增删改查" | 加菜单分支 |
| 7 | 全局 | 没有任何地方把输入转成编号，`mark_done`/`remove` 无调用者 | `parse_id()` + 菜单调用 |
| 8 | `main` | 空输入（`strip()` 后为空串）照样入库 | 判空后 `continue` |
| 9 | `list_all` | `enumerate` 拿到的 `i` 从未使用；打印的是 `t['id']`，序号与 id 混用容易让人对着错行操作 | 要么用 `i`，要么去掉 `enumerate` |
| 10 | `load` | 没校验顶层类型：`todos.json` 是 `{}` 或 `"abc"` 时 `json.load` 不报错，后面 `for t in todos` 以 `TypeError` 崩 | `if not isinstance(data, list): return []` |
| 11 | `load` | `JSONDecodeError` 直接 `return []`，**数据损坏被静默吞掉** | 至少打印警告到 stderr |
| 12 | `save` | 无 `OSError` 处理：磁盘满、文件被 Excel/编辑器占用 → traceback，用户刚输入的内容全丢 | 捕获后提示并返回 False |
| 13 | `save` | 直接 `"w"` 覆盖，写到一半崩溃就损坏原文件 | 临时文件 + `fsync` + `os.replace` 原子替换 |
| 14 | `input` | 未捕获 `EOFError`/`KeyboardInterrupt`，IDE 里 Ctrl+D 或 Ctrl+C 直接 traceback | 统一 `read_line()` 返回 None |
| 15 | `main` | 退出只认中文「退出」，`q`/`exit` 无效 | 支持多种写法 |

---

## 三、P2：规范与可维护性

| # | 问题 | 说明 |
|---|---|---|
| 16 | f-string 嵌套同种引号 `f'...{t['id']}...'` | 只有 Python 3.12+ 合法（PEP 701）。团队里有人用 3.10/3.11 直接 `SyntaxError`。统一"外双内单" |
| 17 | `'done':False`、`ensure_ascii=False` 缺空格 | PEP 8；`ruff format` / `black` 一键解决 |
| 18 | 类型注解过粗：`list`、`dict` | 应为 `list[dict[str, Any]]`；且全是 `#` 注释而非 docstring，`help()` 看不到 |
| 19 | 无模块 docstring、无 `--help` | 别人（包括三个月后的你）不知道这文件干什么 |
| 20 | `Path(__file__).parent` 未 `resolve()` | 通过相对路径/软链接导入时可能拿到非绝对路径 |
| 21 | 函数名 `load`/`save` 与 `json.load`/`json.dump` 语义容易混 | 建议 `load_todos` / `save_todos` |
| 22 | 没有任何测试 | 加一个 `--selftest`，把边界情况固化成断言 |

---

## 四、本次已做的修复（新 `todo.py`，349 行）

**分层**：持久化层（`load_todos` / `save_todos`）→ 业务层（`add_todo` / `find_todo` / `mark_done` / `remove_todo` / `print_all`）→ 交互层（`read_line` / `parse_id` / `interactive`）→ 自检（`selftest`）。

关键改动：

1. `DATA_FILE = Path(__file__).resolve().parent / "todos.json"`，`save()` 与 `load()` 用同一个常量（修复 #1）。
2. `save_todos()` 改为**原子写**：`mkstemp` → 写 → `flush` + `fsync` → `os.replace`（修复 #13、#12）。
3. `remove_todo()` 用列表推导式 + `todos[:] = remain`（修复 #2）。
4. `mark_done()` 找到返回 True，交给调用方 `save()`（修复 #3、#4）。
5. `interactive()` 进循环前 `load_todos()` 一次（修复 #5）。
6. 完整菜单：1 添加 / 2 查看 / 3 完成 / 4 删除 / 5 清空已完成 / q 退出（修复 #6、#7、#15）。
7. `read_line()` 统一兜 `EOFError`/`KeyboardInterrupt`；`parse_id()` 兜非法输入（修复 #14、#8）。
8. `load_todos()` 对「不存在 / 空 / 坏 JSON / 顶层非列表 / 脏记录」全部降级并提示（修复 #10、#11）。
9. 全量类型注解 + docstring + 模块说明（修复 #18、#19）。
10. `--selftest`：22 条断言覆盖增删改查、持久化、损坏降级、中文往返（修复 #22）。

## 五、验证证据

```
$ python todo.py --selftest
✅ 自检通过：增 / 删 / 改 / 查、持久化、损坏降级、中文往返 全部正常。
exit=0
```

脚本化完整交互（添加 2 条 → 查看 → 完成不存在的 999 → 非法输入 abc → 删除 #1 → 查看 → 退出）：

```
已添加 #1：Buy milk
已添加 #2：Write report
[ ]   1  Buy milk  (2026-11-04T17:38)
[ ]   2  Write report  (2026-11-04T17:38)
共 2 条，已完成 0 条，未完成 2 条。
没有编号为 999 的待办。
"abc" 不是数字编号。
已删除 #1
[ ]   2  Write report  (2026-11-04T17:38)
共 1 条，已完成 0 条，未完成 1 条。
[退出码] 0
```

落盘结果正确：

```json
[
  {
    "id": 2,
    "text": "Write report",
    "done": false,
    "created_at": "2026-11-04T17:38"
  }
]
```

## 六、环境侧的修复

| 项目 | 修复内容 |
|---|---|
| `.env` | 去掉值两侧多余的引号；补 `LLM_BASE_URL` / `LLM_MODEL`（`code/00_hello_llm.py` 与 `code/01_minimal_agent.py` 读的是这两个名字）；真实 key 原样保留 |
| `.env.example` | 新建，占位符版本，可安全提交 |
| `.gitignore` | **在项目根目录新建**（原来只有 `.venv/.gitignore` 和 `.idea/.gitignore`，都管不到根目录的 `.env`），实测 `git check-ignore -v .env` → 命中 `.gitignore:7:.env` |
| `DATA_FILE` 遗留数据 | 已迁移到 `todos.json`（「做数学题」那条保住了） |

## 七、仍需你处理的一件事

`.venv` 里还缺 `python-dotenv` 和 `requests`（`1.py` / `brain.py` / `python_study.py` 需要）。本次 `pip install` 被 DSH 沙箱的文件权限挡住了（pip 无法往它自己新建的临时目录里写），请在你自己的 PowerShell 里跑一次：

```powershell
cd "C:\Users\admin\Desktop\study"
.\.venv\Scripts\Activate.ps1
python -m pip install python-dotenv requests
```

装完 `python code\00_hello_llm.py --check` 才会全绿。
